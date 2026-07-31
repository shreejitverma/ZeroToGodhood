"""Listing 251.1 - Python 3.3 (2012): collections.ChainMap, layered lookups as one mapping.

Layered configuration is everywhere: command-line overrides environment, which
overrides a config file, which overrides built-in defaults. The usual way to
resolve it was to MERGE the layers into one dict with repeated dict.update() -
which COPIES everything and loses the layers, so you cannot see where a value
came from or change one layer independently. Python 3.3's collections.ChainMap
groups several mappings into a single view searched in order, WITHOUT copying:
a lookup returns the first layer that has the key, writes go to the first layer,
and the underlying dicts stay separate and live. Deep Q owns the dict; this is
the release that made 'search these mappings in priority order' a first-class
object. Verified on current interpreters.
"""

from collections import ChainMap


def main() -> None:
    print("--- a ChainMap searches its maps in order, first match wins ---")
    defaults = {"color": "black", "size": "medium", "verbose": False}
    from_file = {"color": "blue"}
    from_cli = {"size": "large"}
    config = ChainMap(from_cli, from_file, defaults)   # highest priority first
    print(f"  config['size']    : {config['size']}   (from CLI - highest layer)")
    print(f"  config['color']   : {config['color']}   (from file - CLI had none)")
    print(f"  config['verbose'] : {config['verbose']}   (from defaults - the fallback)")
    print("  each lookup walks the maps left to right and returns the first hit.")
    print("  CLI beats file beats defaults - priority resolution with no merge")

    print("--- no copying: the underlying maps stay separate and LIVE ---")
    from_file["color"] = "green"                 # mutate a layer after building
    print(f"  after from_file['color']='green', config['color'] : {config['color']}")
    print("  the ChainMap holds REFERENCES to the original dicts, not a copy, so")
    print("  changing a layer changes what the chain sees. a merged dict would")
    print("  have frozen the values at merge time")

    print("--- writes go to the FIRST map only ---")
    config["size"] = "small"                     # writes land in from_cli
    print(f"  config['size']='small' -> from_cli is now : {from_cli}")
    print(f"  defaults untouched : {defaults}")
    print("  assigning through the chain writes to the first (highest-priority)")
    print("  map, leaving the lower layers - like your on-disk defaults -")
    print("  pristine. you override without mutating the base")

    print("--- new_child(): push a temporary top layer (scopes, overrides) ---")
    base = ChainMap({"a": 1, "b": 2})
    scoped = base.new_child({"b": 99})           # a new highest layer
    print(f"  base['b']   : {base['b']}")
    print(f"  scoped['b'] : {scoped['b']}  (the new child shadows it)")
    print(f"  scoped['a'] : {scoped['a']}  (falls through to the parent)")
    print("  new_child() adds a fresh top layer without touching the parent -")
    print("  exactly how nested scopes and temporary overrides work: shadow in")
    print("  the child, fall through to the parent, discard the child to undo")

    print("--- keys() and items() reflect the merged view (first-wins) ---")
    view = ChainMap({"x": 1}, {"x": 2, "y": 3})
    print(f"  dict(ChainMap({{x:1}}, {{x:2, y:3}})) : {dict(view)}")
    print("  iterating shows each key once, with the first layer's value")
    print("  winning (x=1, not 2). the chain presents ONE mapping while keeping")
    print("  the layers underneath")

    print("--- the constraint answered ---")
    print("  layering configs meant merging dicts, which copied everything and")
    print("  destroyed the layers. ChainMap (3.3) makes 'search these mappings")
    print("  in priority order' a live view: first-match lookup, writes to the")
    print("  top layer, new_child() for scopes, no copying. the layers stay")
    print("  separate, inspectable, and independently mutable")


if __name__ == "__main__":
    main()
