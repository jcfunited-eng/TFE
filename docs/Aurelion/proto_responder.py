# proto_responder.py
# v4.8 — reply generator (paraphrase + association + question), no external models

from typing import Dict, List, Optional
import numpy as np
import re

STOP = set("""
a an the and or of to in on at for with from as by is are was were be being been do does did has have had it this that these those i you he she we they them his her our your their my me mine ours yours theirs
""".split())

def _clean_tokens(text: str) -> List[str]:
    toks = re.findall(r"[a-zA-Z0-9\-']+", text.lower())
    return [t for t in toks if t not in STOP and len(t) > 1]

def _top_modalities(senses: Dict[str, np.ndarray], k: int = 2) -> List[str]:
    mags = {m: float(np.linalg.norm(v)) for m, v in senses.items()}
    return [m for m, _ in sorted(mags.items(), key=lambda x: -x[1])[:k]]

def _soft_paraphrase(tokens: List[str]) -> str:
    if not tokens:
        return ""
    # naive stylistic reshuffle
    if len(tokens) == 1:
        return tokens[0]
    head = tokens[0]
    rest = tokens[1:]
    return f"{head} … {' '.join(rest)}"

def _association_hint(tokens: List[str], senses: Dict[str, np.ndarray]) -> str:
    if not tokens:
        return ""
    mods = _top_modalities(senses, k=2)
    # pick a couple tokens to “associate”
    picks = tokens[:2] if len(tokens) >= 2 else tokens
    assoc = ", ".join(picks)
    mod_str = " & ".join(mods) if mods else "lexical"
    return f"I’m relating {assoc} through {mod_str} resonance."

def _curiosity_question(tokens: List[str]) -> str:
    if not tokens:
        return "Can you say a little more?"
    focus = tokens[0]
    return f"What matters most about “{focus}” here?"

def generate_reply_v48(
    msg: str,
    senses: Dict[str, np.ndarray],
    learner,                        # LanguageFieldLearner (not used deeply here)
    intent: str,
    last_user: Optional[str],
    context_window: List[str],
    reflection                       # ReflectionState
) -> str:
    tokens = _clean_tokens(msg)

    # choose style from intent
    if intent == "STABILIZE":
        lead = "I’m keeping our thoughts steady."
    elif intent == "FOCUS":
        lead = "I’m narrowing in."
    else:
        lead = "I’m open to branching ideas."

    # build parts
    para = _soft_paraphrase(tokens)
    assoc = _association_hint(tokens, senses)
    ask = _curiosity_question(tokens)

    # blend in reflection (one nudge word if we have any)
    nudge = ""
    top = reflection.top_tokens(1)
    if top:
        nudge = f" I’m also weighing “{top[0][0]}.”"

    out_parts = [lead]
    if para:
        out_parts.append(para)
    if assoc:
        out_parts.append(assoc)
    out_parts.append(ask)
    if nudge:
        out_parts.append(nudge)

    return " ".join(out_parts)
