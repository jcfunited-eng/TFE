"""
GL-CODE-testdream-wC-20260608-003
Test mental time travel: after a conversation, long silence should
produce Guala-recall of past episodes via the DMN.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gl_v5b_substrate import build_guala, hear_and_respond, silence


def main():
    s = build_guala()

    # First, give Guala some experience (multiple conversations)
    print("=" * 70)
    print("PHASE 1: Live some experience")
    print("=" * 70)
    print()

    exchanges = [
        ["hello"],
        ["what", "are", "your", "name"],
        ["are", "you", "dog"],
        ["are", "you", "man"],
        ["tell", "me", "about", "dog"],
        ["what", "interests", "you"],
    ]
    for words in exchanges:
        u = hear_and_respond(s, words, response_ticks=20)
        print(f"  Joe: {' '.join(words)}")
        print(f"  Guala: {' '.join(u) if u else '(silent)'}")
        print()

    print(f"Tick after phase 1: {s.tick_count}")

    # Now, sustained silence — let DMN take over
    print()
    print("=" * 70)
    print("PHASE 2: Long silence — DMN takes over, mental time travel")
    print("=" * 70)
    print()

    # Run silence in chunks and report each
    for chunk in range(4):
        chunk_start = s.tick_count
        s.run(40)
        words_spoken = []
        for t in range(chunk_start, s.tick_count):
            for f in s.log[t]:
                if f.startswith("say_"):
                    words_spoken.append((t, f[4:]))
        # also list which episodes fired
        episodes_fired = set()
        for t in range(chunk_start, s.tick_count):
            for f in s.log[t]:
                if f.startswith("episode_"):
                    episodes_fired.add(f)

        words_only = [w for _, w in words_spoken]
        print(f"Silence chunk {chunk+1} (ticks {chunk_start}-{s.tick_count}):")
        print(f"  Guala (uttered): {' '.join(words_only) if words_only else '(silent)'}")
        print(f"  Episodes firing: {sorted(episodes_fired)}")
        print()

    # Show how many episode weights have grown
    print("=" * 70)
    print("PHASE 3: What did each episode capture?")
    print("=" * 70)
    print()

    for i in range(8):
        ep = f"episode_{i}"
        # Find this episode's strongest outgoing wires
        outgoing = [c for c in s.conns
                    if c.src == ep and c.dst.startswith("say_")
                    and c.weight > 0.1]
        outgoing.sort(key=lambda c: c.weight, reverse=True)
        # And strongest incoming
        incoming = [c for c in s.conns
                    if c.dst == ep and c.weight > 0.1]
        incoming.sort(key=lambda c: c.weight, reverse=True)

        print(f"Episode {i}:")
        if outgoing:
            print(f"  Replays words: {', '.join(f'{c.dst[4:]}({c.weight:.2f})' for c in outgoing[:6])}")
        else:
            print(f"  No strong word-replay wires")
        if incoming:
            top = incoming[:5]
            print(f"  Captured from: {', '.join(f'{c.src}({c.weight:.2f})' for c in top)}")
        print()


if __name__ == "__main__":
    main()
