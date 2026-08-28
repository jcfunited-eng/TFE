NAME = "pay 87 cents using only quarters, dimes, and nickels"
SLOTS = [("quarters", list(range(4))), ("dimes", list(range(9))),
         ("nickels", list(range(18)))]
LAWS = [("the-count-must-balance (from: physics/conservation "
         "through money's bookkeeping + mathematics/counting)",
         "expr",
         "25*quarters + 10*dimes + 5*nickels == 87")]
RANK = None
