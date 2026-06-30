# GL-CMD-CURRICULUM-LOCK-RELEASE-EVE-20260629-46

Dispatch brief per user message 2026-06-30.

§2.1 Drop outer `with self.lock:` in read_sentence (was L1649).
Body runs unlocked; per-word read_word calls retain internal RLock.
Slices 30-sentence × 1-2s hold into per-word <5ms windows.

§2.2 Lift _current_episode to sentence-local.
Pass as current_episode= kwarg to read_word. Falls back to
self._current_episode for direct-caller compat.

§2.3 Lift _negation_pending to sentence-local mutable list [count].
Pass as negation_state= kwarg to read_word. Falls back to
self._negation_pending for direct-caller compat.

§2.4 Direct read_word callers (line 4801): default None kwargs → compat.
