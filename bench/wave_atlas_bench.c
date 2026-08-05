/* wave_atlas_bench.c — Phase 1 (measurement-only) C port of the WaveAtlas
 * spillover write hot path (tools/wave_spillover.py: spill_write, _commit_cell,
 * Cell), for benchmark comparison against the Python baseline. Not wired into
 * production (dsf_ai_service/v4/wave_atlas.py, tools/wave_spillover.py are
 * untouched) -- this is a standalone .so loaded only by
 * bench/wave_atlas_bench.py.
 *
 * Algorithm fidelity: reproduces spill_write's DECISION logic (same final_chi
 * for the same inputs, single-threaded) exactly, including:
 *   - saturation check (aggregate_strength > SATURATION_THRESHOLD)
 *   - ±CHI_BAND neighbor scan in ascending d order, strict "affinity >
 *     best_affinity" tie-break (first-seen wins on exact ties)
 *   - vdot(a, b) = sum_i conj(a_i) * b_i, |vdot| for coherence
 *   - incremental unit-norm running mean for phase_vec
 *   - hop-limited recursion, implemented here as a loop (not real recursion --
 *     hop_limit can be up to 512, too deep to trust the C call stack for, and
 *     a loop makes per-hop lock accounting far simpler, per dispatch)
 *
 * Concurrency: production's real WaveAtlas is explicitly "lock-free" (see
 * dsf_ai_service/v4/wave_atlas.py module docstring) -- this C port is NOT
 * required to reproduce that lock-free-ness bit-for-bit; it adds real bucket
 * locks specifically so the C port itself is race-free (no lost writes, no
 * corrupted aggregate_strength, no non-unit-norm/NaN phase_vec, no deadlock).
 * The Python *baseline* used for comparison in wave_atlas_bench.py calls the
 * real tools.wave_spillover.spill_write with NO added lock, matching
 * production's actual (lock-free, racy) behavior -- that fidelity requirement
 * lives in the .py file, not here.
 *
 * Locking discipline (see also the long comment on wa_spill_write below):
 * 256 buckets, one mutex per 1024 contiguous chi cells (bucket_of(idx) =
 * idx >> 10, since N_CELLS=262144=2^18 and N_BUCKETS=256=2^8 -> shift by
 * 18-8=10 bits = "top 8 bits of the 18-bit chi index space"). Each hop of a
 * spill_write acquires only the buckets it needs for THAT hop, always in
 * ascending bucket-index order, and either commits while still holding them
 * or releases all of them before the next hop's fresh acquisition. Locks are
 * never carried across hops. This is a standard deadlock-free lock-ordering
 * discipline. It does mean results are not guaranteed bit-identical to a
 * fully serial run under concurrent load (a neighbor cell's state can change
 * between one hop's release and the next hop's read) -- an accepted tradeoff
 * for a best-effort spillover heuristic, matching this codebase's existing
 * "lock-free" design philosophy for this exact class of structure.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <pthread.h>

#define N_CELLS            262144   /* chi index space size (2^18) */
#define N_BUCKETS          256      /* one mutex per 1024 cells (2^8) */
#define BUCKET_SHIFT        10      /* 262144 >> 10 == 256 */
#define CHI_BAND              5     /* spillover search radius */
#define PHASE_COMPLEX        16     /* 16 complex numbers per phase vector */
#define PHASE_FLOATS         32     /* interleaved re0,im0,re1,im1,...       */
#define SATURATION_THRESHOLD 5.0    /* aggregate_strength > this -> saturated */
#define INITIAL_BINDING_CAP   4     /* starting capacity of Cell.bindings   */
#define MAX_BUCKETS_PER_HOP  16     /* idx's bucket + up to 10 neighbor buckets,
                                        16 is generous headroom */

/* ---- data structures (naming matches the dispatch) --------------------- */

typedef struct {
    int64_t motif_id;
    int64_t chi;       /* the chi index this binding actually landed at */
    double  strength;
} Binding;

typedef struct {
    double   aggregate_strength;
    int32_t  is_saturated;
    int32_t  binding_count;
    int32_t  binding_capacity;
    Binding *bindings;                 /* realloc-grown array */
    float    phase_vec[PHASE_FLOATS];  /* 16 complex, re/im interleaved */
    int32_t  has_phase_vec;            /* 0/1 -- C's stand-in for "is None" */
} Cell;

typedef struct {
    Cell           *cells[N_CELLS];        /* sparse: NULL until first write */
    pthread_mutex_t bucket_locks[N_BUCKETS];
} WaveAtlasC;

/* ---- small helpers ------------------------------------------------------ */

static inline int64_t mod_n(int64_t v) {
    int64_t m = v % N_CELLS;
    if (m < 0) m += N_CELLS;
    return m;
}

static inline int32_t bucket_of(int64_t idx) {
    return (int32_t)(idx >> BUCKET_SHIFT);
}

/* Add bucket b to set[] if not already present. *count is updated in place. */
static inline void add_unique_bucket(int32_t *set, int32_t *count, int32_t b) {
    for (int32_t k = 0; k < *count; k++) {
        if (set[k] == b) return;
    }
    set[(*count)++] = b;
}

/* Tiny insertion sort -- set is at most MAX_BUCKETS_PER_HOP elements. */
static inline void sort_buckets_ascending(int32_t *set, int32_t count) {
    for (int32_t i = 1; i < count; i++) {
        int32_t key = set[i];
        int32_t j = i - 1;
        while (j >= 0 && set[j] > key) {
            set[j + 1] = set[j];
            j--;
        }
        set[j + 1] = key;
    }
}

/* ---- commit_cell (caller must already hold the lock for idx's bucket) -- */

/* Mirrors _commit_cell in tools/wave_spillover.py exactly:
 *   1. allocate cell if missing
 *   2. append binding, add strength to aggregate_strength
 *   3. if a phase vector was supplied: incremental unit-norm running mean,
 *      n = binding count AFTER this write
 *   4. recompute saturated = aggregate_strength > SATURATION_THRESHOLD
 */
static void commit_cell_locked(
    WaveAtlasC *a, int64_t idx,
    const float *phase_in, int32_t has_phase_in,
    int64_t motif_id, double strength
) {
    Cell *c = a->cells[idx];
    if (c == NULL) {
        c = (Cell *)calloc(1, sizeof(Cell));
        c->binding_capacity = INITIAL_BINDING_CAP;
        c->bindings = (Binding *)malloc(sizeof(Binding) * (size_t)c->binding_capacity);
        a->cells[idx] = c;
    }

    if (c->binding_count >= c->binding_capacity) {
        c->binding_capacity *= 2;
        c->bindings = (Binding *)realloc(c->bindings,
                                          sizeof(Binding) * (size_t)c->binding_capacity);
    }
    Binding *b = &c->bindings[c->binding_count++];
    b->motif_id = motif_id;
    b->chi = idx;
    b->strength = strength;
    c->aggregate_strength += strength;

    if (has_phase_in) {
        int32_t n = c->binding_count; /* count AFTER the append above */
        if (!c->has_phase_vec) {
            memcpy(c->phase_vec, phase_in, sizeof(float) * PHASE_FLOATS);
            c->has_phase_vec = 1;
        } else {
            double a_frac = (double)(n - 1) / (double)n;
            double b_frac = 1.0 / (double)n;
            for (int i = 0; i < PHASE_FLOATS; i++) {
                double mixed = (double)c->phase_vec[i] * a_frac
                             + (double)phase_in[i] * b_frac;
                c->phase_vec[i] = (float)mixed;
            }
        }
        double sumsq = 0.0;
        for (int i = 0; i < PHASE_FLOATS; i++) {
            double v = (double)c->phase_vec[i];
            sumsq += v * v;
        }
        double nrm = sqrt(sumsq);
        if (nrm > 1e-12) {
            for (int i = 0; i < PHASE_FLOATS; i++) {
                c->phase_vec[i] = (float)((double)c->phase_vec[i] / nrm);
            }
        }
    }

    c->is_saturated = (c->aggregate_strength > SATURATION_THRESHOLD) ? 1 : 0;
}

/* ---- public API ---------------------------------------------------------- */

WaveAtlasC *wa_open(void) {
    WaveAtlasC *a = (WaveAtlasC *)calloc(1, sizeof(WaveAtlasC));
    if (!a) return NULL;
    for (int32_t i = 0; i < N_BUCKETS; i++) {
        pthread_mutex_init(&a->bucket_locks[i], NULL);
    }
    return a;
}

/* wa_spill_write -- loop-based tail-recursion-as-iteration port of spill_write.
 *
 * Per hop:
 *   1. Lock ONLY idx's own bucket and check cells[idx]. If it's missing or
 *      unsaturated, commit right here (still holding that single lock) and
 *      return -- this is the common-case fast path (spec: "usually within
 *      1 bucket") and needs no neighbor scan at all.
 *   2. Otherwise (saturated): release that single lock, then compute the
 *      full set of buckets this hop needs (idx's own bucket + the buckets of
 *      all 2*CHI_BAND neighbors, deduplicated), sort ascending, and acquire
 *      all of them in that order (never hold-and-wait out of order -> no
 *      deadlock across concurrently-running hops/threads).
 *   3. Scan neighbors d = -CHI_BAND..CHI_BAND (skipping 0) in that ascending
 *      order, compute coherence/resistance/affinity per spec, track the best
 *      with strict '>' (first-seen wins ties, matching Python).
 *   4. best_idx's bucket is guaranteed to already be locked (it's one of the
 *      buckets acquired in step 2). If best_cell is saturated and hops remain,
 *      release ALL locks for this hop and loop with idx=best_idx, hop+=1 (a
 *      fresh hop starts its own acquisition from step 1). Otherwise commit at
 *      best_idx while still holding the locks, then release all and return.
 */
int64_t wa_spill_write(
    WaveAtlasC *a, int64_t chi_target,
    const float *phase_vec_in_or_null, int32_t has_phase_vec_in,
    int64_t motif_id, double strength, int32_t hop_limit
) {
    int64_t idx = mod_n(chi_target);
    int32_t hop = 0;

    for (;;) {
        /* --- Step 1: cheap single-bucket probe for the common fast path --- */
        int32_t bi = bucket_of(idx);
        pthread_mutex_lock(&a->bucket_locks[bi]);
        Cell *c = a->cells[idx];
        if (c == NULL || !c->is_saturated) {
            commit_cell_locked(a, idx, phase_vec_in_or_null, has_phase_vec_in,
                                motif_id, strength);
            pthread_mutex_unlock(&a->bucket_locks[bi]);
            return idx;
        }
        pthread_mutex_unlock(&a->bucket_locks[bi]);

        /* --- Step 2: saturated -- build this hop's full bucket set --- */
        int64_t n_idx_arr[2 * CHI_BAND];
        int32_t n_count = 0;
        int32_t bucket_set[MAX_BUCKETS_PER_HOP];
        int32_t bucket_count = 0;

        add_unique_bucket(bucket_set, &bucket_count, bi);
        for (int32_t d = -CHI_BAND; d <= CHI_BAND; d++) {
            if (d == 0) continue;
            int64_t n_idx = mod_n(idx + d);
            n_idx_arr[n_count++] = n_idx;
            add_unique_bucket(bucket_set, &bucket_count, bucket_of(n_idx));
        }
        sort_buckets_ascending(bucket_set, bucket_count);
        for (int32_t i = 0; i < bucket_count; i++) {
            pthread_mutex_lock(&a->bucket_locks[bucket_set[i]]);
        }

        /* --- Step 3: affinity scan, ascending d order, strict '>' --- */
        double norm_in = 0.0;
        if (has_phase_vec_in) {
            double s = 0.0;
            for (int i = 0; i < PHASE_FLOATS; i++) {
                double v = (double)phase_vec_in_or_null[i];
                s += v * v;
            }
            norm_in = sqrt(s);
        }

        int64_t best_idx = n_idx_arr[0];
        double  best_affinity = -1.0;

        for (int32_t k = 0; k < n_count; k++) {
            int64_t n_idx = n_idx_arr[k];
            Cell *n = a->cells[n_idx];
            double coherence, resistance;
            if (n == NULL) {
                coherence = 1.0;
                resistance = 0.0;
            } else {
                if (has_phase_vec_in && n->has_phase_vec && norm_in > 1e-12) {
                    double norm_n_sq = 0.0;
                    for (int i = 0; i < PHASE_FLOATS; i++) {
                        double v = (double)n->phase_vec[i];
                        norm_n_sq += v * v;
                    }
                    double norm_n = sqrt(norm_n_sq);
                    if (norm_n > 1e-12) {
                        /* vdot(a, b) = sum_i conj(a_i) * b_i, a = phase_vec_in,
                         * b = n->phase_vec, complex re/im interleaved:
                         * conj(a_i)*b_i = (a_re*b_re + a_im*b_im)
                         *               + i*(a_re*b_im - a_im*b_re) */
                        double s_re = 0.0, s_im = 0.0;
                        for (int i = 0; i < PHASE_COMPLEX; i++) {
                            double a_re = (double)phase_vec_in_or_null[2 * i];
                            double a_im = (double)phase_vec_in_or_null[2 * i + 1];
                            double b_re = (double)n->phase_vec[2 * i];
                            double b_im = (double)n->phase_vec[2 * i + 1];
                            s_re += a_re * b_re + a_im * b_im;
                            s_im += a_re * b_im - a_im * b_re;
                        }
                        double vdot_abs = sqrt(s_re * s_re + s_im * s_im);
                        coherence = vdot_abs / (norm_in * norm_n + 1e-12);
                    } else {
                        coherence = 1.0;
                    }
                } else {
                    coherence = 1.0;
                }
                resistance = n->aggregate_strength;
            }
            double affinity = coherence / (1.0 + resistance);
            if (affinity > best_affinity) {
                best_affinity = affinity;
                best_idx = n_idx;
            }
        }

        /* --- Step 4: decide commit-here vs. next hop --- */
        Cell *best_cell = a->cells[best_idx]; /* bucket already locked */
        if (best_cell != NULL && best_cell->is_saturated) {
            if (hop + 1 >= hop_limit) {
                commit_cell_locked(a, best_idx, phase_vec_in_or_null,
                                    has_phase_vec_in, motif_id, strength);
                for (int32_t i = 0; i < bucket_count; i++) {
                    pthread_mutex_unlock(&a->bucket_locks[bucket_set[i]]);
                }
                return best_idx;
            }
            for (int32_t i = 0; i < bucket_count; i++) {
                pthread_mutex_unlock(&a->bucket_locks[bucket_set[i]]);
            }
            idx = best_idx;
            hop = hop + 1;
            continue; /* next hop: fresh acquisition from Step 1 */
        } else {
            commit_cell_locked(a, best_idx, phase_vec_in_or_null,
                                has_phase_vec_in, motif_id, strength);
            for (int32_t i = 0; i < bucket_count; i++) {
                pthread_mutex_unlock(&a->bucket_locks[bucket_set[i]]);
            }
            return best_idx;
        }
    }
}

/* Copy a cell's scalar/phase state out. Returns 1 if the cell exists, 0 if
 * NULL. Locks the cell's bucket while copying (bounds-checked-copy pattern,
 * matching bw_get_entry in dsf_ai_service/substrate/binding_window.c). */
int32_t wa_get_cell_snapshot(
    WaveAtlasC *a, int64_t idx,
    double *out_aggregate_strength, int32_t *out_is_saturated,
    int32_t *out_binding_count, float *out_phase_vec_32,
    int32_t *out_has_phase_vec
) {
    int64_t midx = mod_n(idx);
    int32_t bi = bucket_of(midx);
    pthread_mutex_lock(&a->bucket_locks[bi]);
    Cell *c = a->cells[midx];
    if (c == NULL) {
        pthread_mutex_unlock(&a->bucket_locks[bi]);
        return 0;
    }
    *out_aggregate_strength = c->aggregate_strength;
    *out_is_saturated = c->is_saturated;
    *out_binding_count = c->binding_count;
    *out_has_phase_vec = c->has_phase_vec;
    if (c->has_phase_vec) {
        memcpy(out_phase_vec_32, c->phase_vec, sizeof(float) * PHASE_FLOATS);
    } else {
        memset(out_phase_vec_32, 0, sizeof(float) * PHASE_FLOATS);
    }
    pthread_mutex_unlock(&a->bucket_locks[bi]);
    return 1;
}

/* Copy up to max_count motif_ids from a cell's bindings. Returns actual
 * count copied (0 if the cell doesn't exist). Locked, same pattern. */
int32_t wa_get_cell_binding_motif_ids(
    WaveAtlasC *a, int64_t idx, int64_t *out_array, int32_t max_count
) {
    int64_t midx = mod_n(idx);
    int32_t bi = bucket_of(midx);
    pthread_mutex_lock(&a->bucket_locks[bi]);
    Cell *c = a->cells[midx];
    if (c == NULL) {
        pthread_mutex_unlock(&a->bucket_locks[bi]);
        return 0;
    }
    int32_t n = c->binding_count;
    if (n > max_count) n = max_count;
    if (n < 0) n = 0;
    for (int32_t i = 0; i < n; i++) {
        out_array[i] = c->bindings[i].motif_id;
    }
    pthread_mutex_unlock(&a->bucket_locks[bi]);
    return n;
}

void wa_free(WaveAtlasC *a) {
    if (!a) return;
    for (int32_t i = 0; i < N_CELLS; i++) {
        if (a->cells[i]) {
            free(a->cells[i]->bindings);
            free(a->cells[i]);
        }
    }
    for (int32_t i = 0; i < N_BUCKETS; i++) {
        pthread_mutex_destroy(&a->bucket_locks[i]);
    }
    free(a);
}
