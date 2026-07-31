# Chapter 273: Class Patterns

## The constraint

Sequence patterns (Chapter 271) and mapping patterns (Chapter 272) match built-in containers.
But the data a program most wants to dispatch on is often *its own objects*: nodes in an abstract syntax tree, shapes in a geometry hierarchy, a family of event or message classes.
Matching those meant an `isinstance` ladder with attribute access on each branch:

```python
if isinstance(shape, Circle):
    r = shape.radius
    ...
elif isinstance(shape, Rectangle):
    w, h = shape.width, shape.height
    ...
```

Every branch does the type check and then pulls the attributes out, as two separate steps that must stay in sync.
This is exactly the pattern that makes working with typed data hierarchies verbose.

Python 3.10's *class patterns* match an object by its *type* and its *attributes*, binding them in one step.
The constraint they answer: **dispatch on the type and structure of your own objects declaratively**, collapsing the `isinstance`-plus-attribute-access ladder into type-directed patterns.

This chapter is the class-pattern facet of the pattern-matching volume; the type model and `__match_args__` are Deep Volume C's.

## What shipped

A class pattern like `Circle(radius=r)` matches an instance of `Circle` and binds its `.radius` to `r`.
With `__match_args__` (which `@dataclass` sets automatically from the field order), attributes can be matched *positionally*: `Point(x, y)`.
Class patterns nest and respect inheritance.
Listing 273.1 shows all of this on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- class patterns match by TYPE and bind attributes ---
  area(Circle) : 12.56636
  area(Rectangle) : 12.0
  area(Point) : 0.0
  `case Circle(radius=r)` matches an instance of Circle AND binds its
  .radius to r. one pattern does the isinstance check and the
  attribute pull that used to be two separate steps
--- positional matching via __match_args__ (dataclasses set it) ---
  Point.__match_args__ : ('x', 'y')
  describe(Point(x=0, y=0)) : origin
  describe(Point(x=5, y=0)) : on x-axis at 5
  describe(Point(x=2, y=3)) : point (2, 3)
  __match_args__ = ('x', 'y') lets `Point(x, y)` match POSITIONALLY,
  mapping the first sub-pattern to .x and the second to .y. @dataclass
  sets it from the field order, so positional matching just works
--- nested class patterns: match structure several levels deep ---
  origin circle, radius 5.0
  circle centred at (3, 4)
  the sub-pattern for `center` is ITSELF a class pattern Point(0, 0).
  patterns nest, so you match a Circle whose center is the origin in
  one expression - deep structural dispatch on typed objects
--- a class pattern also checks isinstance, so subtypes match ---
  is_point(ColoredPoint(1, 2, 'red')) : True
  `case Point()` matches any Point OR subclass, because the type
  check is an isinstance test (Deep C). a ColoredPoint IS a Point, so
  it matches - type-directed dispatch that respects inheritance
--- the constraint answered ---
  matching YOUR objects meant isinstance checks plus attribute
  access, branch after branch. class patterns (3.10) do both at once:
  `Type(attr=pattern)` checks the type and binds attributes, positional
  matching via __match_args__, patterns nest, and subclasses match.
  typed data got declarative, structural dispatch
```

## Why each part answers the constraint

**Type and attributes, together.**
The first block shows `area` dispatching on shape types: `case Circle(radius=r)` matches a `Circle` *and* binds its `.radius` to `r`, `case Rectangle(width=w, height=h)` matches a rectangle and binds its dimensions, and `case Point()` matches any point.
One pattern does the `isinstance` check and the attribute extraction that were previously two coupled steps - the ladder collapses into declarative type-directed dispatch.

**Positional matching via `__match_args__`.**
The second block shows the convenience that makes class patterns concise.
`Point.__match_args__` is `('x', 'y')` - set automatically by `@dataclass` from the field order - and it lets `Point(x, y)` match *positionally*, mapping the first sub-pattern to `.x` and the second to `.y`.
So `Point(0, 0)` matches the origin, `Point(x, 0)` matches a point on the x-axis, and so on, without spelling out `x=` and `y=` each time.
This is why matching dataclasses feels natural out of the box.

**Nested patterns.**
The third block shows class patterns nesting: `Circle(center=Point(0, 0), radius=r)` matches a `Circle` whose `center` attribute is *itself* matched by the class pattern `Point(0, 0)`.
So "a circle centered at the origin" is one expression, and "a circle centered anywhere, capturing the coordinates" is another.
Patterns compose to any depth, giving deep structural dispatch over trees of typed objects - exactly what an AST walker or a nested-data handler needs.

**Inheritance-aware type checks.**
The fourth block shows that a class pattern's type check is an `isinstance` test, so subclasses match: `case Point()` matches a `ColoredPoint`, because a `ColoredPoint` *is* a `Point`.
The dispatch respects inheritance (Deep Volume C), so a pattern for a base class handles all its subclasses - the same substitutability that makes `isinstance` useful, now driving pattern selection.

## The two-track note

The type model that class patterns rest on - `isinstance` semantics, the method resolution order, and `__match_args__` as the protocol that maps positional sub-patterns to attributes - is Deep Volume C's to develop, and dataclasses (Chapter 13) are what set `__match_args__` automatically.
What the timeline records is the class-pattern facet of the 3.10 release: type-and-attribute matching, positional matching via `__match_args__`, nesting, and inheritance-aware dispatch.
The modern consequence, verified above, is that matching over typed object hierarchies - ASTs, shape families, event classes - is declarative structural dispatch, and that dataclasses and class patterns are a natural pairing (define the data with `@dataclass`, dispatch on it with `match`).

## Where this lands

Class patterns are what make `match` genuinely powerful for object-oriented, typed data.
Reach for them whenever you dispatch on a family of your own classes and pull out their attributes - AST nodes, geometric shapes, message types, state objects.
Define the data as dataclasses to get `__match_args__` (and thus positional matching) for free; use keyword sub-patterns (`Type(attr=pattern)`) when positional order is unclear; nest patterns to match structure several levels deep; and rely on the `isinstance` semantics so a base-class pattern covers its subclasses.
Deep Volume C explains the type model and `__match_args__`; this chapter is the record of the class-pattern facet of structural pattern matching.
