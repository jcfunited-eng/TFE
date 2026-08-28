NAME = "seat five guests at a round table"
GUESTS = ["alice", "bob", "cara", "dan", "eve"]
SLOTS = [("chair1", GUESTS), ("chair2", GUESTS), ("chair3", GUESTS),
         ("chair4", GUESTS), ("chair5", GUESTS)]
RING = ["chair1", "chair2", "chair3", "chair4", "chair5"]
LAWS = [
  ("one-body-one-place (from: physics/exclusion)", "alldiff", None),
  ("alice and bob feud (from: this party)", "not-beside",
   ("alice", "bob")),
  ("cara steadies dan (from: this party)", "beside",
   ("cara", "dan")),
]
RANK = None
