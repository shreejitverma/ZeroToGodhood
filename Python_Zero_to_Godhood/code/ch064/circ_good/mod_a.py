def a_value():
    return "A"
def combined():
    from ch064.circ_good import mod_b   # imported at call time, fully loaded
    return a_value() + mod_b.b_value()
