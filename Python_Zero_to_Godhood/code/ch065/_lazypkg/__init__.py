"""A package that lazily loads its 'heavy' submodule via PEP 562 module __getattr__.
Importing the package does NOT import heavy; the first access to pkg.heavy does."""
import importlib

def __getattr__(name):
    # Called only for attributes not found normally (PEP 562).
    if name == "heavy":
        module = importlib.import_module(f"{__name__}.heavy")
        globals()[name] = module          # cache so __getattr__ is not called again
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
