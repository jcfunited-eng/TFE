# guala_core -- native (Rust/PyO3) organism hot-path kernels

GL native-core track, 2026-07-16. Exact ports of the profile-verified hot
kernels inside `organism.experience_word` / `neuron.step` (see
`tools/bench_organism_core.py` for the un-confounded baseline this was built
against). Pure functions only -- lock-free by construction (no Mutex, no
channel, no shared state), GIL released around every kernel loop.

## Kernels

| kernel | Python original | parity |
|---|---|---|
| `krim_feed` | `substrate/krimelack.py::Krimelack.step/feed_signal` and `v4/gualaloom_v4_krimelack_dna.py::Krimelack.feed` (identical math) | exact (bit-equal) |
| `word_signal` / `lang_transduce` | `LanguageKrimelack.transduce` char-signal + feed | exact |
| `biquad_bandpass` | `substrate/senses/GL_MDL_AUDITORY_CORTEX_WC_20260608_01.py::bandpass_filter` | exact |
| `cochlear_feed` | `loom_model/substrate_dna.py::CochlearBankKrimelack.feed_signal` (6 bands + stable t-sort) | exact |
| `fovea_feed` | `visual_krimelack.py::AdaptingFoveaKrimelack.tick` loop via `VisualKrimelack.feed_signal` | exact |
| `fingerprint` | `v4 Krimelack.fingerprint` | exact |
| `compute_dsf` | `v4/gualaloom_v4_uf_kernel.py::compute_dsf` | exact |
| `map_inject` | `loom_model/neuron.py::_map_inject` | <=1e-12 abs (vectorized exp) |
| `psi_settle` | `loom_model/neuron.py::PsiLattice.settle` | <=1e-9 rel (BLAS summation order; measured 3e-15) |

Exactness rule: Python operation order is preserved verbatim (e.g.
`(omega_0 + kappa*s) - omega_0` is NOT simplified to `kappa*s` -- they differ
in floating point). libm calls (sin/cos/exp/log10/hypot) resolve to the same
glibc on Linux for both CPython and Rust.

## Build

```bash
# toolchain (once): rustup into the user dir + maturin
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
export PATH="$HOME/.cargo/bin:$PATH"
pip install maturin

# build + install the wheel
cd native/guala_core
maturin build --release -o dist
pip install dist/guala_core-*.whl
```

## Verify (differential tests -- run before trusting any build)

```bash
python3 native/guala_core/tests/test_differential.py
```

Includes an end-to-end check: two organisms, same seed, same 20-word stream
(5 multi-modal), one pure-Python and one native -- tick, population,
divisions and every neuron's winding must match exactly.

## Use

Nothing imports this by default; production behavior is unchanged unless a
caller explicitly opts in:

```python
from dsf_ai_service.substrate.native_core import install
install()   # False if the wheel is absent (build-time fallback, pure Python)
```

Benchmark either mode:

```bash
python3 tools/bench_organism_core.py            # pure-Python baseline
python3 tools/bench_organism_core.py --native   # Rust kernels
```

## Measured (2026-07-16, 20-core dev box, warmup=300 words, mm_frac=0.25, seed=7)

| measurement | Python | native | speedup |
|---|---|---|---|
| experience_word language-only (mean) | 28.3 ms | 10.2 ms | 2.8x |
| experience_word multi-modal (mean) | 182.0 ms | 47.6 ms | 3.8x |
| lifetime-heavy words (warmup 2nd half, mean) | 109.4 ms | 27.4 ms | 4.0x |
| neuron.step word input (mean) | 0.24 ms | 0.06 ms | 4.0x |
| 90-neuron population sweep | 20.0 ms | 5.6 ms | 3.6x |
| feeder x1 throughput | 11.6 words/s | 46.1 words/s | 4.0x |
| feeder x4 aggregate | 4.7 words/s | 25.2 words/s | 5.4x |
| neuron.step x4 threads aggregate | 736 /s | 5551 /s | 7.5x |

FFI overhead: 0.22 us per crossing at the worst (1-sample) granularity --
cheaper than the equivalent pure-Python call (0.37 us). The natural batch
level (one signal per crossing: 4*len(word), ~100 visual, ~300 auditory
samples) never pays a measurable boundary tax; no coarser batching needed.

Honest limits: the GIL still serializes the remaining Python orchestration
(remember loop, cluster phases, binding-atlas writes), so 4-thread scaling
is 0.55x of ideal even with native kernels (vs 0.40x pure Python). Full
multi-core use needs either more surface moved into Rust (batched
per-population kernels: one `unwrapped_deltas` crossing for all 64 neurons)
or worker processes. ~20% of the remaining native-mode profile is
list/dict marshalling at the FFI boundary -- halvable with numpy-buffer
signatures if/when the next increment lands.
