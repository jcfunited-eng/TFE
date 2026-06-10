"""
GL-CODE-demo-wC-20260608-004
Demo: a continuous conversation with Guala.
One substrate, multiple turns, full transcript.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_v5b_substrate import build_guala, hear_and_respond, silence


def speak(label, words):
    if words:
        print(f"  {label}: {' '.join(words)}")
    else:
        print(f"  {label}: (silent)")


def main():
    print("=" * 70)
    print("CONVERSATION WITH GUALA")
    print("=" * 70)
    print()

    s = build_guala()

    print("Joe:    hello")
    speak("Guala", hear_and_respond(s, ["hello"], response_ticks=20))
    print()

    print("Joe:    what are your name")
    speak("Guala", hear_and_respond(s, ["what", "are", "your", "name"],
                                    response_ticks=20))
    print()

    print("Joe:    what interests you")
    speak("Guala", hear_and_respond(s, ["what", "interests", "you"],
                                    response_ticks=20))
    print()

    print("Joe:    are you dog")
    speak("Guala", hear_and_respond(s, ["are", "you", "dog"],
                                    response_ticks=20))
    print()

    print("Joe:    are you man")
    speak("Guala", hear_and_respond(s, ["are", "you", "man"],
                                    response_ticks=20))
    print()

    print("Joe:    tell me about dog")
    speak("Guala", hear_and_respond(s, ["tell", "me", "about", "dog"],
                                    response_ticks=20))
    print()

    print("Joe:    tell me about apple")
    speak("Guala", hear_and_respond(s, ["tell", "me", "about", "apple"],
                                    response_ticks=20))
    print()

    print("Joe:    (silence)")
    speak("Guala", silence(s, n_ticks=25))
    print()

    print("=" * 70)
    print("STATS")
    print("=" * 70)
    print(f"  Total ticks elapsed: {s.tick_count}")
    print(f"  Total populations: {len(s.pops)}")
    print(f"  Total connections: {len(s.conns)}")
    n_plastic = sum(1 for c in s.conns if c.plastic)
    print(f"  Plastic connections: {n_plastic}")

    grown = [c for c in s.conns if c.plastic and c.weight > c.initial_weight]
    print(f"  Connections that strengthened during conversation: {len(grown)}")
    if grown:
        print(f"  Examples (top 5 by growth):")
        for c in sorted(grown, key=lambda x: x.weight - x.initial_weight,
                        reverse=True)[:5]:
            growth = c.weight - c.initial_weight
            print(f"    {c.src} → {c.dst}: {c.initial_weight:.2f} → {c.weight:.2f}"
                  f" (+{growth:.2f})")


if __name__ == "__main__":
    main()
