from ch064.circ_bad import mod_a        # mod_a is only half-loaded here
def b_value():
    return "B"
TITLE = "module B uses " + mod_a.a_value()   # mod_a.a_value not defined yet!
