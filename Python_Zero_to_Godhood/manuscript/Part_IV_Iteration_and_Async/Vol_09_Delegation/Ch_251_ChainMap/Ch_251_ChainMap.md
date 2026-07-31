# Chapter 251: ChainMap

## The constraint

Layered configuration is one of the most common structures in real software.
A setting has a built-in default; a config file may override it; an environment variable may override that; a command-line flag may override everything.
The rule is "highest-priority layer that mentions the key wins," and the layers below still matter for the keys the higher ones do not set.

The usual way to resolve this was to *merge* the layers into one dictionary:

```python
config = {}
config.update(defaults)
config.update(from_file)
config.update(from_env)
config.update(from_cli)
```

This works for lookup, but it throws away information.
It *copies* every value into a new dict, so the layers no longer exist as separate things - you cannot ask "which layer did this value come from?", you cannot change one layer and have the resolved view update, and you cannot cheaply push a temporary override and pop it again.
The merge flattens a structured, layered thing into a snapshot.

The constraint Python 3.3 (2012) answered: **make "search these mappings in priority order" a first-class object that preserves the layers - no copying, live underlying maps, writes directed to the top layer.**

This is a two-track chapter.
The dictionary it is built on - the hash table, lookup cost - belongs to Deep Volume Q.
What this chapter owns is the release: the day layered lookup became a standard container instead of a lossy merge.

## What shipped

`collections.ChainMap` groups several mappings into a single view.
A lookup walks the maps in order and returns the first that has the key; writes go to the first map; the underlying dicts stay separate and live; and `new_child` pushes a fresh top layer.
Listing 251.1 shows all of this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- a ChainMap searches its maps in order, first match wins ---
  config['size']    : large   (from CLI - highest layer)
  config['color']   : blue   (from file - CLI had none)
  config['verbose'] : False   (from defaults - the fallback)
  each lookup walks the maps left to right and returns the first hit.
  CLI beats file beats defaults - priority resolution with no merge
--- no copying: the underlying maps stay separate and LIVE ---
  after from_file['color']='green', config['color'] : green
  the ChainMap holds REFERENCES to the original dicts, not a copy, so
  changing a layer changes what the chain sees. a merged dict would
  have frozen the values at merge time
--- writes go to the FIRST map only ---
  config['size']='small' -> from_cli is now : {'size': 'small'}
  defaults untouched : {'color': 'black', 'size': 'medium', 'verbose': False}
  assigning through the chain writes to the first (highest-priority)
  map, leaving the lower layers - like your on-disk defaults -
  pristine. you override without mutating the base
--- new_child(): push a temporary top layer (scopes, overrides) ---
  base['b']   : 2
  scoped['b'] : 99  (the new child shadows it)
  scoped['a'] : 1  (falls through to the parent)
  new_child() adds a fresh top layer without touching the parent -
  exactly how nested scopes and temporary overrides work: shadow in
  the child, fall through to the parent, discard the child to undo
--- keys() and items() reflect the merged view (first-wins) ---
  dict(ChainMap({x:1}, {x:2, y:3})) : {'x': 1, 'y': 3}
  iterating shows each key once, with the first layer's value
  winning (x=1, not 2). the chain presents ONE mapping while keeping
  the layers underneath
--- the constraint answered ---
  layering configs meant merging dicts, which copied everything and
  destroyed the layers. ChainMap (3.3) makes 'search these mappings
  in priority order' a live view: first-match lookup, writes to the
  top layer, new_child() for scopes, no copying. the layers stay
  separate, inspectable, and independently mutable
```

## Why each part answers the constraint

**First-match lookup implements priority.**
The first block shows the resolution: with `ChainMap(from_cli, from_file, defaults)`, `size` comes from the CLI layer, `color` falls through to the file layer (the CLI had none), and `verbose` falls all the way through to defaults.
Each lookup walks the maps left to right and returns the first hit - priority resolution without ever building a merged dict.

**No copying keeps the layers live.**
The second block shows the property a merge destroys.
Mutating `from_file` *after* building the ChainMap changes what the chain sees, because the ChainMap holds *references* to the original dicts, not copies.
A merged dict would have frozen the values at merge time; the ChainMap reflects the current state of its layers.

**Writes target the top layer.**
The third block shows the write semantics: assigning `config["size"] = "small"` lands in `from_cli`, the highest-priority map, and leaves `defaults` untouched.
This is exactly the behavior a layered config wants - you override at the top without mutating your base defaults, which might be shared, on-disk, or read-only in intent.

**`new_child` models scopes.**
The fourth block shows the operation that makes ChainMap more than a config tool.
`base.new_child({"b": 99})` returns a new ChainMap with a fresh top layer that shadows `b` while `a` falls through to the parent - and the parent is untouched.
This is precisely how nested scopes and temporary overrides work: shadow in the child, fall through to the parent, and discard the child to undo.
Python's own name resolution has this shape, and ChainMap makes it a reusable object.

**The merged view is still one mapping.**
The fifth block confirms that iteration presents a single, deduplicated mapping with first-wins values: `dict(ChainMap({"x": 1}, {"x": 2, "y": 3}))` is `{"x": 1, "y": 3}`.
So a ChainMap is usable anywhere a mapping is expected - it *looks* like one flat dict - while keeping the layers intact underneath.

## The two-track note

The dictionary machinery - the hash table, the O(1) per-layer lookup that makes walking a few layers cheap - is Deep Volume Q's to detail.
What the timeline records is the release act: in 3.3, `collections.ChainMap` turned layered lookup from a lossy merge into a live, structured view.
The modern consequence, verified above, is that ChainMap is the standard tool for layered configuration and scoped overrides - and that its no-copy, layers-preserved design is what distinguishes it from the flatten-and-forget merge it replaced.

## Where this lands

`ChainMap` is a small container that captures a very common structure precisely.
Reach for it whenever you have priority-ordered layers of settings - defaults under file under environment under command line - and want lookups resolved by priority while keeping the layers separate, inspectable, and independently mutable.
Reach for `new_child` when you need a temporary override you can discard, the way a scope pushes and pops.
Use a plain merged dict only when you genuinely want a flattened snapshot and do not care where values came from.
Deep Volume Q explains the dictionary underneath; this chapter is the record of the release that made layered lookup a first-class, non-destructive view.
