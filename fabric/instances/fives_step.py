NAME = ("THE STEP: one more five-bundle coin lands on a pile "
        "whose ones place reads 0 or 5 — where can the ones "
        "place go? (laid by hand; the imagining element's job "
        "once it exists)")
SLOTS = [("current", [0, 5]), ("coin", [0, 5]),
         ("next", list(range(10))), ("carry", [0, 1])]
LAWS = [("column-count (from: mathematics/bundles+counting)",
         "expr", "current + coin == next + 10*carry")]
RANK = None
