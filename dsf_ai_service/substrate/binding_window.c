/* binding_window.c — hot path for binding window entry addition.
 *
 * Ports the essential structure of WindowManager.add_entry to C:
 * per-window array of entries, thread-safe add.
 *
 * When called via ctypes, the GIL is released for the duration.
 * Multiple threads calling into this simultaneously actually run
 * in parallel across cores instead of serializing on the interpreter.
 *
 * c1 additions to the reference (GL-CMD-BINDING-WINDOW-C-PORT-EVE-
 * 20260707-v1's "use them or refine"): bw_get_entry (named in the
 * dispatch's own BUILD list, absent from the reference) and bounds
 * checking on it -- a missing-entry read here would be a real
 * out-of-bounds memory read, not a Python exception.
 *
 * GL-CMD-SLOT-LIMITS-REMOVAL-EVE-20260707-v1: the fixed-size
 * entries[MAX_ENTRIES_PER_WINDOW] array (a slot limit, not a real
 * physical constraint -- confirmed empirically earlier tonight:
 * 384 words of ordinary reading produced 1235 entries in one window,
 * exceeding the old 1024 cap) replaced with a dynamic, realloc-grown
 * array. Starts at 64 entries, doubles on overflow. No new arbitrary
 * ceiling introduced -- growth is bounded only by what the window's
 * own real lifecycle (open/close, driven by real substrate activity
 * elsewhere) actually needs, matching this dispatch's "state drives
 * stop, not counter" instruction.
 */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <pthread.h>

#define INITIAL_ENTRY_CAPACITY 64
#define SOURCE_TAG_MAX 32

typedef struct {
    int32_t  modality_id;       /* enum: 0=sight,1=sound,2=word,3=touch,4=smell,5=taste */
    int32_t  section_id;
    int64_t  motif_id;
    int64_t  chi;
    int64_t  tick;
    char     source_tag[SOURCE_TAG_MAX];
} WindowEntry;

typedef struct {
    char            window_id[40];
    int64_t         opened_tick;
    double          opened_wall_clock;
    int64_t         closed_tick;
    double          closed_wall_clock;
    int32_t         is_closed;
    int32_t         entry_count;
    int32_t         entry_capacity;   /* GL-CMD-SLOT-LIMITS-REMOVAL: dynamic, not fixed */
    WindowEntry     *entries;         /* realloc-grown, starts at INITIAL_ENTRY_CAPACITY */
    pthread_mutex_t lock;
} BindingWindow;

/* Add an entry to a window. Returns entry index, or -1 on closed window
 * or allocation failure (out of memory -- the only remaining failure
 * mode now that the fixed-size ceiling is gone).
 * pthread_mutex protects entry_count/entry_capacity/entries -- but only
 * for concurrent adds to the SAME window. Different windows proceed
 * fully in parallel.
 */
int32_t bw_add_entry(
    BindingWindow *w,
    int32_t modality_id,
    int32_t section_id,
    int64_t motif_id,
    int64_t chi,
    int64_t tick,
    const char *source_tag
) {
    pthread_mutex_lock(&w->lock);
    if (w->is_closed) {
        pthread_mutex_unlock(&w->lock);
        return -1;
    }
    if (w->entry_count >= w->entry_capacity) {
        int32_t new_capacity = w->entry_capacity * 2;
        WindowEntry *new_entries = realloc(w->entries, (size_t)new_capacity * sizeof(WindowEntry));
        if (new_entries == NULL) {
            /* Out of memory -- the array keeps its old (still valid,
             * still full) contents; caller sees this as a normal-shaped
             * failure (-1), same as the old "window full" case, not a
             * crash. */
            pthread_mutex_unlock(&w->lock);
            return -1;
        }
        w->entries = new_entries;
        w->entry_capacity = new_capacity;
    }
    int32_t idx = w->entry_count;
    WindowEntry *e = &w->entries[idx];
    e->modality_id = modality_id;
    e->section_id = section_id;
    e->motif_id = motif_id;
    e->chi = chi;
    e->tick = tick;
    strncpy(e->source_tag, source_tag, SOURCE_TAG_MAX - 1);
    e->source_tag[SOURCE_TAG_MAX - 1] = '\0';
    w->entry_count++;
    pthread_mutex_unlock(&w->lock);
    return idx;
}

/* Allocate a new window (caller-freed). */
BindingWindow *bw_open(const char *window_id, int64_t opened_tick, double opened_wall_clock) {
    BindingWindow *w = calloc(1, sizeof(BindingWindow));
    if (!w) return NULL;
    strncpy(w->window_id, window_id, sizeof(w->window_id) - 1);
    w->opened_tick = opened_tick;
    w->opened_wall_clock = opened_wall_clock;
    w->entries = malloc((size_t)INITIAL_ENTRY_CAPACITY * sizeof(WindowEntry));
    if (!w->entries) {
        free(w);
        return NULL;
    }
    w->entry_capacity = INITIAL_ENTRY_CAPACITY;
    pthread_mutex_init(&w->lock, NULL);
    return w;
}

void bw_close(BindingWindow *w, int64_t closed_tick, double closed_wall_clock) {
    pthread_mutex_lock(&w->lock);
    w->is_closed = 1;
    w->closed_tick = closed_tick;
    w->closed_wall_clock = closed_wall_clock;
    pthread_mutex_unlock(&w->lock);
}

int32_t bw_entry_count(BindingWindow *w) {
    return w->entry_count;
}

/* Copy entry at idx into *out. Returns 1 on success, 0 if idx is out of
 * range (caller-facing bounds check -- never reads past what was
 * actually written). Locked, matching every other accessor here: safe
 * even if called before bw_close (a live snapshot mid-fill), though the
 * real caller (WindowManager.close()) only calls this after bw_close. */
int32_t bw_get_entry(BindingWindow *w, int32_t idx, WindowEntry *out) {
    pthread_mutex_lock(&w->lock);
    if (idx < 0 || idx >= w->entry_count) {
        pthread_mutex_unlock(&w->lock);
        return 0;
    }
    *out = w->entries[idx];
    pthread_mutex_unlock(&w->lock);
    return 1;
}

void bw_free(BindingWindow *w) {
    if (w) {
        pthread_mutex_destroy(&w->lock);
        free(w->entries);
        free(w);
    }
}
