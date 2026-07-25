"""A harmless local module used to demonstrate sys.path search order."""
ORIGIN = "local shadowdir"
def pi():
    return 3.0     # deliberately wrong, to prove which module was imported
