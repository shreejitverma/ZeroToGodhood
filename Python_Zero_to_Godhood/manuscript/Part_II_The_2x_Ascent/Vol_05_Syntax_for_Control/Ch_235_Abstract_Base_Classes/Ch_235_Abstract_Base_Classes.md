# Chapter 235: Abstract Base Classes

## The constraint

Python is a duck-typed language: the question it wants to ask about a value is "does it *behave* like the thing I need?" - does it iterate, does it have a length, can I index it, can I add to it.
But for its first seventeen years, the tool for asking about a value's type, `isinstance()`, asked a different and stricter question: "does it *inherit* from this class?"
Those two questions disagree constantly.
A `str` behaves like a sequence in every way that matters, but it does not inherit from any shared "Sequence" base class, so an `isinstance(x, SomeSequenceBase)` check would say no.
The result was that idiomatic Python code avoided `isinstance` almost entirely - it was the wrong question - and instead used `try`/`except` or `hasattr` to probe for behavior, which worked but scattered the type question across ad-hoc checks.

There was a second, related gap.
When you designed a base class meant to define an interface - "a repository has `get` and `put`" - nothing enforced it.
A subclass could forget to implement a method, and the omission would not surface until some later call site hit a `NotImplementedError`, or worse, an `AttributeError`, far from the actual mistake.

The constraint Python 2.6 (2008, PEP 3119) answered was both at once: **make `isinstance` able to answer the behavioral question a duck-typed language actually asks, and give interfaces a way to enforce their contract at construction time.**

This is a two-track chapter.
The metaclass machinery underneath - `ABCMeta`, how `__subclasshook__` and `__instancecheck__` hook into `isinstance`, how registration records a virtual subclass - belongs to Deep Volume C (types, descriptors, metaclasses).
What this chapter owns is the release: the day `isinstance` learned to answer "does it behave like one?", and abstract methods began enforcing themselves.

## What shipped

Python 2.6 added the `abc` module (`ABC`, `ABCMeta`, `@abstractmethod`) and, built on it, the `collections.abc` and `numbers` hierarchies - abstract base classes for the language's own protocols.
An ABC can recognize a class *structurally* (by the methods it defines), *adopt* an unrelated class by registration, and *enforce* that its abstract methods are implemented.
Listing 235.1 shows all three on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- ABCs answer BEHAVIOURAL isinstance, without shared inheritance ---
  isinstance([], Sequence)   : True
  isinstance('hi', Sequence) : True
  isinstance({}, Mapping)    : True
  isinstance({}, Sequence)   : False
  list, str, and dict do NOT inherit from these ABCs, yet isinstance
  says list/str are Sequences and dict is a Mapping. the ABC answers
  'does it behave like one?', which is the duck-typing question
--- __len__ alone makes you a Sized: the structural hook ---
  Bag defines only __len__
  isinstance(Bag(), Sized) : True
  issubclass(Bag, Sized)   : True
  Bag never mentions Sized, but Sized.__subclasshook__ checks for a
  __len__ method and says yes. the ABC recognises the SHAPE of the
  class, not its ancestry - structural typing built into isinstance
--- registration: declare an unrelated class a virtual subclass ---
  Number.register(Temperature)
  isinstance(Temperature(20), Number) : True
  but Temperature.__mro__ has no Number : True
  register() makes isinstance say yes WITHOUT touching the class or
  its bases - a virtual subclass. you can retrofit a third-party
  class into an ABC hierarchy you do not control
--- @abstractmethod: a contract the interpreter enforces ---
  instantiating the ABC raises : TypeError(Can't instantiate abstract class Repository without an implementation for abstract methods 'get', 'put')
  a concrete subclass implementing both methods works : 1
  a class with an unimplemented @abstractmethod cannot be
  instantiated - the contract is enforced at construction, not left
  to a NotImplementedError at some later call site
--- the constraint answered ---
  duck typing asks 'does it behave like X?' but isinstance asked
  'does it inherit X?'. ABCs (2.6) reconciled them: __subclasshook__
  recognises shape, register() adopts unrelated classes, and
  @abstractmethod enforces the contract. isinstance finally answers
  the behavioural question a duck-typed language actually asks
```

## Why each part answers the constraint

**`isinstance` finally answers the behavioral question.**
The first block is the reconciliation.
`list` and `str` are `Sequence`s and `dict` is a `Mapping`, according to `isinstance` - even though none of them inherit from those ABCs.
And `dict` is correctly *not* a `Sequence`.
The check now reports what the value *does*, not what it descends from, which is exactly the question duck typing has always been asking informally.
`isinstance(x, Sequence)` is finally a meaningful, correct check in a duck-typed language.

**Structural recognition: shape, not ancestry.**
The second block shows the mechanism that makes it work for your own classes.
`Bag` defines only `__len__` and mentions `Sized` nowhere, yet `isinstance(Bag(), Sized)` and `issubclass(Bag, Sized)` are both `True`.
`Sized.__subclasshook__` inspects the class for a `__len__` method and answers yes on that basis alone.
The ABC recognizes the *shape* of the class - a form of structural typing wired directly into `isinstance`, requiring no cooperation from `Bag` at all.

**Registration: adopting classes you do not control.**
The third block shows the other adoption path.
`Number.register(Temperature)` declares `Temperature` a *virtual* subclass of `Number`: `isinstance(Temperature(20), Number)` becomes `True`, yet `Number` appears nowhere in `Temperature.__mro__` - the class and its bases are untouched.
This is the escape hatch for interfaces that cannot be detected structurally: you can retrofit a third-party class into an ABC hierarchy you do not own, without subclassing or modifying it.

**`@abstractmethod` enforces the contract at construction.**
The fourth block closes the second gap.
`Repository` declares `get` and `put` as `@abstractmethod`; attempting to instantiate it raises `TypeError` immediately, naming the unimplemented methods.
A concrete `DictRepo` that implements both instantiates and works.
The enforcement happens at *construction* - the moment you try to make an object that cannot honor its interface - not at some distant call site when the missing method is finally invoked.
That is the difference between a contract the interpreter checks and a convention it merely hopes you followed.

## The two-track note

The metaclass foundations - `ABCMeta` overriding `__instancecheck__` and `__subclasscheck__`, the caching of subclass checks, how `__subclasshook__` composes with registration, why an ABC uses a metaclass at all - are Deep Volume C's to develop.
What the timeline records is the release act: in 2.6, `isinstance` was taught to answer the behavioral question through structural hooks and registration, and abstract methods gained the power to refuse construction.
The modern consequence, verified above, is that `collections.abc` is the standard vocabulary for "is this a sequence, a mapping, a set, a sized thing?", and `@abstractmethod` is the standard way to define an interface Python actually enforces.
Both work byte-for-byte as they did when they shipped.

## Where this lands

Abstract base classes were Python's answer to a real tension: a duck-typed language whose one type-checking tool asked the wrong question.
By 2.6, `isinstance` could finally mean "behaves like," `collections.abc` gave that meaning a shared vocabulary, and `@abstractmethod` turned interfaces from documentation into enforced contracts.
This groundwork is also what the later `typing.Protocol` (Part V) generalizes into static structural typing - the same "shape, not ancestry" idea, checked by a type checker instead of at runtime.
Deep Volume C explains the metaclass machinery; this chapter is the record of the release that reconciled `isinstance` with the way Python actually thinks about types.

This closes Volume 5 (Syntax for Control): the 2.4-2.6 arc whose through-line is delegated control - decorators and `with` hand a function or block to something that wraps it, the unified `try` and conditional expression sharpened control flow, `send` made generators drivable, key-based sorting delegated ordering to a key function, and ABCs delegated the type question to behavior. Each feature moved a decision from the caller's hands into a well-defined mechanism.
