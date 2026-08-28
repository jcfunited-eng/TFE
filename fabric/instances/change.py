NAME = "pay 87 cents with the fewest coins"
SLOTS = [("quarters", list(range(4))), ("dimes", list(range(9))),
         ("nickels", list(range(18))), ("pennies", list(range(88)))]
LAWS = [("the-count-must-balance (from: physics/conservation "
         "through money's bookkeeping + mathematics/counting)",
         "expr",
         "25*quarters + 10*dimes + 5*nickels + pennies == 87")]
RANK = "quarters + dimes + nickels + pennies"
