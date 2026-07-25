def b_value():
    return "B"
def combined():
    from ch064.circ_good import mod_a    # deferred: mod_a fully loaded by call time
    return mod_a.a_value() + b_value()
