# Loom synthetic-word spike test retirement — 2026-07-27

## Retired cases

The following cases enqueued typed `probeword` strings and required those
strings to inject sensory or `language` spikes:

1. `dsf_ai_service/loom_model/tests/test_pickle_roundtrip_wiring.py::
   test_worker_loop_injects_on_word_item`
2. `dsf_ai_service/loom_model/tests/test_sensory_spike_gate.py::
   test_word_branch_injects_regardless_of_sensory_flag_unset`
3. `dsf_ai_service/loom_model/tests/test_sensory_spike_gate.py::
   test_word_branch_injects_regardless_of_sensory_flag_zero`
4. `dsf_ai_service/loom_model/tests/test_sensory_spike_gate.py::
   test_word_branch_injects_regardless_of_sensory_flag_one`

The production organism now correctly rejects all four operations with
`word-derived synthetic sensory fields are retired`. Typed characters are not
physical sound, sight, touch, smell, or taste evidence and cannot mint sensory
activity.

Both mixed test files were replaced completely. Their active pickle
round-trip, runtime-reference cleanup, spike-bus wiring, sensory gate, and
physically supplied sensory-item injection tests remain intact. No production
code or sensory boundary was changed.
