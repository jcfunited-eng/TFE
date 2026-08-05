# STDP snapshot physical-stimulus reconciliation — 2026-07-27

Three tests in
`dsf_ai_service/tests/test_debug_stdp_state.py`
used `brain.step("dog", modality="language")` to manufacture activity and
expected the retired `_word_neuron_map` to grow.

The complete test file was replaced. Those snapshot tests now stimulate the
real organism sensory queue, require that no word-neuron mapping is minted,
and continue to verify fire, spike delivery, read-only observation, and
execution budget. All other endpoint, isolation, and runaway-fire diagnostic
proofs remain.

No production code or sensory authority was changed.
