from ch064.circ_bad import mod_b        # runs mod_b's body now
def a_value():
    return "A"
TITLE = "module A uses " + mod_b.b_value()   # needs mod_b.b_value at import time
