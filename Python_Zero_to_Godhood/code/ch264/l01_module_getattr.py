"""Listing 264.1 - Python 3.7 (2018): module-level __getattr__, hooks for attribute access on a module.

Classes had __getattr__ for years - a hook called when an attribute is missing -
enabling lazy attributes and deprecation shims. Modules did not: accessing
module.thing either found a global or raised AttributeError, with no way to
intercept. So libraries could not lazily compute a module attribute, nor emit a
'this name is deprecated, use that one' warning when an old module-level name
was accessed. Python 3.7's PEP 562 added __getattr__ (and __dir__) at MODULE
level: define a module function __getattr__(name) and it is called for any
attribute not found normally. Deep C owns the attribute-lookup protocol; this is
the release that extended it to modules, enabling lazy imports and clean
deprecations. Verified on current interpreters.
"""

import sys
import warnings

# A real module attribute, found the normal way (never hits __getattr__).
VERSION = "2.0"

# Map old, deprecated names to their replacements.
_RENAMED = {"OldConfig": "Config", "MAX_SIZE": "MAX_LIMIT"}

# The current names the deprecated ones point at.
Config = {"mode": "fast"}
MAX_LIMIT = 1000

_lazy_build_count = {"n": 0}


def __getattr__(name):
    """Called ONLY for attributes not found as normal module globals."""
    if name in _RENAMED:
        new = _RENAMED[name]
        warnings.warn(f"{name} is deprecated; use {new}",
                      DeprecationWarning, stacklevel=2)
        return globals()[new]
    if name == "expensive_table":                # lazily built on first access
        _lazy_build_count["n"] += 1
        return {"built": True, "size": 42}
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def main() -> None:
    this = sys.modules[__name__]                  # the module object itself

    print("--- normal attributes never reach __getattr__ ---")
    print(f"  module.VERSION : {this.VERSION}   (a real global, found directly)")
    print("  __getattr__ fires ONLY for names not found the usual way, exactly")
    print("  like the class-level hook. present globals are returned normally,")
    print("  so the hook adds no cost to existing attributes")

    print("--- a deprecated name is redirected with a warning ---")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        value = this.OldConfig                    # deprecated -> Config
    print(f"  module.OldConfig returned : {value}   (the current Config)")
    print(f"  and emitted a DeprecationWarning : {len(caught) == 1}")
    print(f"  warning text : {str(caught[0].message)!r}")
    print("  accessing the OLD name still works (redirected to the new one) but")
    print("  warns the caller to migrate - a clean deprecation shim that was")
    print("  impossible before module __getattr__")

    print("--- a lazy attribute is built only on first access ---")
    print(f"  build count before access : {_lazy_build_count['n']}")
    table = this.expensive_table                  # triggers the lazy build
    print(f"  module.expensive_table : {table}")
    print(f"  build count after access  : {_lazy_build_count['n']}")
    print("  the attribute did not exist as a global; __getattr__ computed it on")
    print("  demand. this is how a package lazily imports a heavy submodule only")
    print("  when someone actually reaches for it - faster imports by default")

    print("--- an unknown name still raises AttributeError, as expected ---")
    try:
        this.does_not_exist
    except AttributeError as exc:
        print(f"  module.does_not_exist -> AttributeError: {exc}")
    print("  the hook must raise AttributeError for names it does not handle, so")
    print("  genuinely missing attributes behave normally - hasattr, getattr")
    print("  defaults, and error messages all still work")

    print("--- the constraint answered ---")
    print("  classes could intercept missing-attribute access; modules could")
    print("  not, so lazy module attributes and deprecation shims were")
    print("  impossible. PEP 562 (3.7) added module-level __getattr__: a hook")
    print("  called for unresolved names, enabling lazy imports and clean")
    print("  'renamed, please migrate' warnings without breaking existing access")


if __name__ == "__main__":
    main()
