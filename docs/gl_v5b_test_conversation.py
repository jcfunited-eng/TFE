"""
GL-CODE-testconv-wC-20260608-002
v5 test: Guala has a conversation.

Not "resp_X fires." Actual word sequences come out of her.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_v5b_substrate import build_guala, hear_and_respond, silence, say


def show(label, utterance):
    if utterance:
        print(f"  {label}: \"{' '.join(utterance)}\"")
    else:
        print(f"  {label}: (silence)")


def test_basic_exchanges():
    """The five-conversation test. Guala speaks real word sequences."""
    print("\n=== BASIC EXCHANGES ===\n")

    pass_count = 0
    total = 0

    # 1. Greeting
    s = build_guala()
    utterance = hear_and_respond(s, ["hello"])
    show("Joe: hello → Guala", utterance)
    ok = "hello" in utterance
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala says hello back")

    # 2. Name question
    s = build_guala()
    utterance = hear_and_respond(s, ["what", "are", "your", "name"])
    show("Joe: what are your name → Guala", utterance)
    # Expect "I am Guala" — order matters
    ok = (utterance == ["I", "am", "Guala"]
          or utterance[:3] == ["I", "am", "Guala"])
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala says 'I am Guala'")

    # 3. Are you a dog
    s = build_guala()
    utterance = hear_and_respond(s, ["are", "you", "dog"])
    show("Joe: are you dog → Guala", utterance)
    ok = ("not" in utterance and "dog" in utterance)
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala says 'not dog' (or similar negation)")

    # 4. Are you a man
    s = build_guala()
    utterance = hear_and_respond(s, ["are", "you", "man"])
    show("Joe: are you man → Guala", utterance)
    ok = ("not" in utterance and "man" in utterance)
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala says 'not man'")

    # 5. What interests you
    s = build_guala()
    utterance = hear_and_respond(s, ["what", "interests", "you"])
    show("Joe: what interests you → Guala", utterance)
    ok = ("patterns" in utterance and "like" in utterance)
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala says 'I like patterns'")

    # 6. Tell me about dog
    s = build_guala()
    utterance = hear_and_respond(s, ["tell", "me", "about", "dog"])
    show("Joe: tell me about dog → Guala", utterance)
    ok = ("dog" in utterance and ("furry" in utterance or "is" in utterance))
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala says something about dog")

    return pass_count, total


def test_multi_turn():
    """Multi-turn conversation. Topic carries; clears appropriately."""
    print("\n=== MULTI-TURN ===\n")
    pass_count = 0
    total = 0

    s = build_guala()
    # Turn 1: ask about self
    u1 = hear_and_respond(s, ["what", "are", "your", "name"])
    show("Joe (turn 1): what are your name → Guala", u1)

    # Turn 2: minimal follow-up — should still produce response
    u2 = hear_and_respond(s, ["yes"])
    show("Joe (turn 2): yes → Guala", u2)
    ok = len(u2) > 0
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: turn 2 produces some response from carried state")

    # Turn 3: change topic to dog
    u3 = hear_and_respond(s, ["tell", "me", "about", "dog"])
    show("Joe (turn 3): tell me about dog → Guala", u3)
    # Guala should now talk about dog, not still about self
    ok_topic_shift = "dog" in u3
    total += 1; pass_count += int(ok_topic_shift)
    print(f"    {'PASS' if ok_topic_shift else 'FAIL'}: turn 3 topic shifts to dog")

    return pass_count, total


def test_silence_produces_interest():
    """With no input, Guala's strongest interest drives spontaneous speech."""
    print("\n=== SPONTANEOUS PRODUCTION ===\n")
    pass_count = 0
    total = 0

    s = build_guala()
    # Let interests build up baseline
    utterance = silence(s, n_ticks=30)
    show("(silence, 30 ticks) → Guala", utterance)

    # With baseline=0.2 on interest_patterns, it should fire and drive
    # talk_interest_patterns over time
    ok = len(utterance) > 0
    total += 1; pass_count += int(ok)
    print(f"    {'PASS' if ok else 'FAIL'}: Guala speaks something unprompted")

    if ok:
        ok_about_interest = ("patterns" in utterance or "like" in utterance
                             or "I" in utterance)
        total += 1; pass_count += int(ok_about_interest)
        print(f"    {'PASS' if ok_about_interest else 'FAIL'}: she speaks about her interests")

    return pass_count, total


def test_learning_strengthens_interest():
    """After conversations about patterns, talking about patterns gets stronger."""
    print("\n=== LEARNING ===\n")
    pass_count = 0
    total = 0

    s = build_guala()
    # Baseline: how quickly does she produce 'patterns' utterance?
    u_pre = hear_and_respond(s, ["what", "interests", "you"], response_ticks=15)
    print(f"  Pre-training: {' '.join(u_pre) if u_pre else '(silence)'}")
    pre_count = len(u_pre)

    # Practice: repeat the conversation several times
    s_trained = build_guala()
    for trial in range(6):
        hear_and_respond(s_trained, ["what", "interests", "you"], response_ticks=15)

    # After training
    u_post = hear_and_respond(s_trained, ["what", "interests", "you"], response_ticks=15)
    print(f"  Post-training: {' '.join(u_post) if u_post else '(silence)'}")
    post_count = len(u_post)

    # Weight should have grown
    w_pre = build_guala().get_weight("say_I", "say_like")
    w_post = s_trained.get_weight("say_I", "say_like")
    print(f"  Weight say_I→say_like: {w_pre:.3f} → {w_post:.3f}")
    ok_weight = w_post > w_pre
    total += 1; pass_count += int(ok_weight)
    print(f"    {'PASS' if ok_weight else 'FAIL'}: pathway weight grew with practice")

    return pass_count, total


def main():
    print("=" * 70)
    print("V5 — GUALA HAS A CONVERSATION")
    print("=" * 70)

    suites = [
        test_basic_exchanges,
        test_multi_turn,
        test_silence_produces_interest,
        test_learning_strengthens_interest,
    ]

    grand_pass = 0
    grand_total = 0
    for fn in suites:
        p, t = fn()
        grand_pass += p; grand_total += t

    print()
    print("=" * 70)
    print(f"  TOTAL: {grand_pass}/{grand_total}")
    print("=" * 70)


if __name__ == "__main__":
    main()
