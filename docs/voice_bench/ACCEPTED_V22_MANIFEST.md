# Accepted voice bench v22 — proof manifest (2026-09-02)

Joe's acceptance: "Yep that's it" on bench v22, full board.

## Benchmark source (exact accepted file)

- File: docs/voice_bench/toy_vocal_organ_bench_v22.html
- SHA-256: becda71bbe0e4f54c065345cfa736be19d8860cd92faf1549171355484057589
- This is a byte-identical copy of the published artifact page at
  acceptance time ("Toy Vocal Organ", bench v22).

## Canonical render protocol

The bench varies each press on purpose (per-say variation): a global
press counter seeds pitch (±3.5%), pace (±7%), and the RNGs. Hashes are
therefore defined ONLY under this exact protocol:

1. Fresh page state (pressCount = 0), all dials at their HTML defaults
   (f0 220, oq 0.60, asym 3, jit 0.8, shim 3; throat dials as shipped).
2. Call utter() once per gesture, in exactly this order:
   c-ahh, c-ohh, c-eee, c-ay, c-uhoh, c-sss, c-shh, c-mmm, c-mama,
   c-see, c-shoe.
3. Hash the raw Float32Array handed to the audio buffer (little-endian
   bytes, before any playback), SHA-256.

Engine caveat: Math.sin/cos/exp are not bit-specified across JS
engines. These hashes are reproduced on V8 (Node 18 / Chrome). Another
engine may differ in last-bit rounding; the audible output is the same.
Cross-engine verification should compare waveforms within tolerance
(peak sample delta < 1e-5), not hashes.

## Accepted output hashes (V8, protocol above)

| gesture | samples | sha256 |
|---|---|---|
| c-ahh  | 27796 | 03b444cbb00143dc9f01f7c16ea89335ec70d8adea67cb97fa2dbe532bcb1d94 |
| c-ohh  | 26219 | 281782cead9e70aaca0e62b2e728d13a6d46ce1c6e0bdf97a9cdd4694272684b |
| c-eee  | 28001 | c0902b30b4d6cddf0dff98b8cc0d1ead4c10449a53b9b36effaa8d45bb7febaa |
| c-ay   | 24854 | c96463645f557fadedae4eb88efc21209a63f3d6c9153a6ed1e40fdae8475ead |
| c-uhoh | 21790 | 0a8a17b442c2613d943e3ec14ba4c8c29edc52f1c2f5becc150b603c68322e90 |
| c-sss  | 17129 | b1da75eabbb0d9aad2cb5b5d0faab7961c6d85fa075173f37172186f103d83e7 |
| c-shh  | 19900 | c22719db5a8e121d0727e02659458a8280a52cdcfb3eaf849a245acc54af719e |
| c-mmm  | 24278 | 693f2c166f63ebc0edfb3b28876648915140a66e7b0203c51ea35c6c7fee5b65 |
| c-mama | 25554 | 5f7c373d8cdd3e49851c04b15cb3713412033917684cc3a1adb76c99ff75c713 |
| c-see  | 23172 | bfb6235fe59e692c96c66932c04fd939d0f2ecfd0aa1fffbbc60b8501a69db85 |
| c-shoe | 15525 | f84eefad31d043f85d0a4a414f30d57590a661bd196b7ddbe227bbd15d058cf3 |

Sample rate 32000 Hz, mono. Reproduce: extract the <script> block from
the source file, stub document/AudioContext (any records of the buffers
handed to createBufferSource), run the protocol, hash.

Version note: v20 was the version live when the consonant recipe was
first filed; v21–v22 changed ONLY the "c-shoe" gesture (vowel rounding
glide, then spoken-length trim). v22 is the accepted final; all other
gestures are byte-identical to v20 under this protocol.
