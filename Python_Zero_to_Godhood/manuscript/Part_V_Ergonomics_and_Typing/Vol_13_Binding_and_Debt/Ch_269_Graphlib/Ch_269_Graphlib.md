# Chapter 269: Graphlib

## The constraint

"Do these things in an order that respects their dependencies" is one of the most universal problems in software.
A build system must compile a module before whatever imports it.
A task scheduler must run a job after everything it waits on.
A package installer must install dependencies before dependents.
A spreadsheet must recalculate a cell after the cells it references.
Every one of these is the same underlying operation: a *topological sort* of a directed graph - producing a linear order in which every node comes after everything it depends on.

The algorithm is not hard, but it is subtle in exactly one place: *cycles*.
If the dependencies form a loop (A needs B, B needs C, C needs A), there is *no* valid order, and a naive implementation typically handles this badly - looping forever, silently dropping the nodes in the cycle, or producing a plausible-looking but wrong order.
And because the standard library had no topological sort, everyone re-implemented it, and a great many of those re-implementations had the cycle bug.

The constraint Python 3.9 (2020) answered: **put a correct topological sort in the standard library** - one that produces a valid order, detects cycles explicitly, and supports parallel execution - so nobody has to re-derive it and get the cycle handling wrong.

This chapter owns no Deep-Volume mechanism; topological sorting is a graph algorithm, not a language feature.
What it owns is the release: the day dependency ordering became batteries-included.

## What shipped

`graphlib.TopologicalSorter` lets you declare each node with the nodes it depends on, then produces a valid linear order via `static_order()`, raises `CycleError` on an impossible graph, and offers a wave-at-a-time parallel interface (`prepare`/`get_ready`/`done`).
Listing 269.1 shows all of it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- declare dependencies; static_order() gives a valid linear order ---
  a valid build order : ['eggs', 'flour', 'electricity', 'batter', 'oven', 'cake']
  eggs before batter  : True
  batter before cake  : True
  every node appears AFTER the things it depends on. that is a
  topological sort: a linear order consistent with all dependencies,
  which is exactly a correct build/execution sequence
--- add(node, *deps): the dependency direction ---
  add('cake', 'batter', 'oven') reads 'cake DEPENDS ON batter, oven',
  so batter and oven come BEFORE cake in the output. you declare what
  each thing NEEDS; the sorter works out the order
--- cycles are detected and reported, not looped forever ---
  a->b->c->a raised CycleError : nodes are in a cycle
  a dependency cycle has NO valid order, and a hand-rolled sort often
  loops forever or silently drops nodes on one. TopologicalSorter
  raises CycleError naming the cycle - the bug most people's version
  gets wrong
--- the parallel mode: which nodes are runnable RIGHT NOW ---
  waves of concurrently-runnable nodes : [['eggs', 'electricity', 'flour'], ['batter', 'oven'], ['cake']]
  get_ready() returns every node whose dependencies are ALL done, so
  each wave can run in PARALLEL. this is the scheduler interface: run
  a wave, mark it done, ask what unlocked - the basis of a build
  system's parallel executor
--- the constraint answered ---
  ordering work by dependencies is a universal need and a topological
  sort, re-implemented everywhere with buggy cycle handling.
  graphlib.TopologicalSorter (3.9) made it standard: declare deps, get
  a valid order, get CycleError on impossible graphs, and get a
  wave-at-a-time parallel scheduler - correct, batteries-included
```

## Why each part answers the constraint

**A valid linear order.**
The first block declares a small dependency graph (a cake needs batter and an oven; batter needs eggs and flour; the oven needs electricity) and gets back an order in which every node follows everything it depends on: eggs and flour before batter, batter and oven before cake.
That is a topological sort - a linear sequence consistent with all the dependencies, which is exactly a correct build or execution order.

**The dependency direction is declarative.**
The second block clarifies the API's reading: `add("cake", "batter", "oven")` means "cake *depends on* batter and oven," so those come *before* cake in the output.
You declare what each node *needs*, and the sorter computes the order - you never specify the order yourself, which is the point.

**Cycles are detected, not mishandled.**
The third block is the part that justifies a standard implementation.
A graph with `a -> b -> c -> a` has no valid order, and `static_order()` raises `CycleError` rather than looping forever or silently dropping nodes.
This is precisely the case hand-rolled topological sorts get wrong, and having it handled correctly - with an error that names the cycle - is the single biggest reason to use the library version over a quick reimplementation.

**Parallel scheduling.**
The fourth block shows the capability beyond a static order: the `prepare`/`get_ready`/`done` interface.
`get_ready()` returns every node whose dependencies are *all* satisfied - a "wave" of nodes that can run *in parallel* - and after you mark them `done`, the next `get_ready()` returns whatever they unlocked.
The verified waves show it: first everything with no dependencies (eggs, electricity, flour), then what those unlock (batter, oven), then cake.
This is the exact interface a parallel build executor needs - run a wave concurrently, mark it complete, ask what became runnable - and it comes for free with the sorter.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; `graphlib` is a graph-algorithm library built on ordinary data structures.
What the timeline records is the release act: in 3.9, `graphlib.TopologicalSorter` put a correct topological sort - with proper cycle detection and a parallel-execution interface - in the standard library.
The modern consequence, verified above, is that dependency ordering is a standard tool rather than a re-derived algorithm, and the cycle-handling bug that plagued hand-rolled versions is simply not something you have to get right yourself anymore.

## Where this lands, and the close of Binding and Debt

`graphlib.TopologicalSorter` is a clean example of the standard library absorbing a genuinely universal algorithm that people kept reimplementing incorrectly.
Reach for it whenever you need to order work by dependencies - build steps, task pipelines, migration sequences, resource initialization - and use the `prepare`/`get_ready`/`done` interface when you want to run independent work concurrently.
Trust its `CycleError` to catch the impossible graphs that a hand-rolled sort would mishandle.
No Deep Volume owns a graph mechanism; this chapter is the record of the release that made topological ordering correct and batteries-included.

This closes Volume 13, Binding and Debt.
The volume's thesis was that 3.9 (and 3.8) paid down debt that earlier choices had accumulated - the LL(1) parser's limitations, typing's rough edges, and a scattering of missing ergonomics.
Its chapters span that range: the walrus operator and positional-only parameters (Chapter 14), the PEG parser and dict-union operators (Chapter 15), typing Protocols (Chapter 16), and the quality-of-life additions gathered here - the f-string `=` specifier, `cached_property`, `removeprefix`/`removesuffix`, and `graphlib`.
Part V concludes with Volume 14, the single feature large enough to warrant a volume of its own: structural pattern matching, which the new PEG parser (Chapter 15) is what finally made possible.
