"""loom_cognition.py — GL-CMD-BIGRAM-DELETE-EVE-20260629-34: GualaCognition deleted.

The GualaCognition bigram model was silenced in GL-CMD-ORGANBRAIN-SILENCE-23
and deleted from the substrate in GL-CMD-BIGRAM-DELETE-34. This file is retained
as an empty module so existing imports don't fail during any transition; it should
be removed entirely once all import references are confirmed gone.

Audit findings (GL-RPT-COGNITION-LEARN-AUDIT-C1-20260628-33):
- GualaCognition had no functional consumer after say() was silenced
- trans/starts/vocab were pure bigram training state
- All 12 _cognition_learn() call sites converted to read_sentence() or deleted
"""
