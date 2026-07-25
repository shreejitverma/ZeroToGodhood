from ch083.svc.clock import now   # imported INTO app's namespace
def timestamp():
    return "at " + now()
