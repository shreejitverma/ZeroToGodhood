# Chapter 250: Unittest Mock

## The constraint

A unit test should exercise one unit of code in isolation, quickly and deterministically.
But real code depends on things a unit test must not actually invoke: a payment gateway, a clock, a database, an email service, a remote API.
Calling the real collaborator in a test is slow, flaky, and often destructive - you do not want your test suite charging credit cards.

So you need a *test double*: a stand-in object that looks enough like the real collaborator to satisfy the code under test, records how it was called so the test can make assertions, and returns whatever the test scripts it to return.
Before Python 3.3, the standard library had no such tool, so people hand-wrote fake classes - a different ad-hoc `FakeMailer` in every project, each reimplementing "record the arguments" and "return this canned value" from scratch.
The excellent third-party `mock` library had solved the problem well, but it was an external dependency.

The constraint Python 3.3 (2012) answered was simply: **make test doubles batteries-included** - adopt `mock` into the standard library as `unittest.mock`, so recording calls, scripting returns, simulating failures, and temporarily replacing real objects are all standard tools.

This chapter owns no Deep-Volume mechanism - mocking is a testing technique built from the object model, not a language feature.
What it owns is the release: the day test doubles stopped being hand-rolled and became part of the standard library.

## What shipped

`unittest.mock` provides `Mock` and `MagicMock` (objects that record every call and let you script return values and exceptions) and `patch` (which temporarily replaces a real object with a mock and restores it afterward).
Listing 250.1 shows the core of it on today's interpreters.

Verified output (CPython 3.13.5):

```text
--- a Mock records how it was called ---
  notify(...) returned : queued
  mailer.send.called      : True
  mailer.send.call_count  : 1
  called with args        : call('ada@x.io', 'Welcome')
  the Mock stood in for a real mailer: it recorded the call and
  returned the scripted 'queued'. no real email, full record of how
  the code under test used its collaborator
--- assert_called_with: state the expected interaction ---
  assert_called_with(...) passed (no exception): the code called
  send with exactly those arguments. this is how you test BEHAVIOUR
  - what the code did to its dependency - not just its return value
  asserting the WRONG args raised AssertionError, as it should
--- side_effect: make a mock raise, or return a sequence ---
  first call  : 1
  second call : 2
  third call raises : ValueError(boom)
  side_effect scripts a SEQUENCE of returns (or exceptions), so you
  can simulate retries, transient failures, and exhausted resources
--- MagicMock supports dunder operations too ---
  len(magicmock) : 3
  magicmock[0]   : x
  a plain Mock does not implement __len__/__getitem__; MagicMock does,
  so it can stand in for list-like or dict-like collaborators
--- patch(): replace a real object for the duration of a block ---
  inside patch, send_email(...) : sent
  fake_send.called : True
  outside patch, send_email is the real function again : True
  patch() swapped the real send_email for a mock inside the block and
  restored it after - so a test never touches the real service, and
  the replacement is automatically undone
--- the constraint answered ---
  testing code with external dependencies needed stand-ins that
  record calls and script returns - hand-written differently every
  time. unittest.mock (3.3) made them standard: Mock records and
  scripts, side_effect simulates failure, patch() swaps reals for
  fakes and restores them. test doubles became batteries-included
```

## Why each part answers the constraint

**A Mock records and scripts.**
The first block shows the core behavior.
A `Mock` stands in for a mailer: `notify` calls `mailer.send(...)`, and the mock records that the call happened (`called`, `call_count`), captures the arguments (`call_args`), and returns the scripted `"queued"` value - all with no real email sent.
The mock gives the code under test something to call and gives the test a complete record of how it was called.

**Assertions test behavior, not just output.**
The second block shows `assert_called_with("ada@x.io", "Welcome")` passing, and the wrong-argument version raising `AssertionError`.
This is the deeper value of mocks: they let you test *what the code did to its collaborator* - the interaction - not merely what it returned.
Verifying that `notify` sent the welcome email to the right address is an assertion about behavior that a return-value check could never make.

**`side_effect` simulates failure.**
The third block shows `side_effect` scripting a *sequence*: return `1`, then `2`, then raise `ValueError`.
This is how you test the hard paths - retry logic, transient failures, exhausted resources - by making the collaborator behave badly on cue.
Simulating a service that fails on the third call is trivial; reproducing it with a real service is nearly impossible.

**MagicMock covers dunder operations.**
The fourth block shows why `MagicMock` exists: a plain `Mock` does not implement `__len__` or `__getitem__`, but `MagicMock` does, so it can stand in for a collaborator that is indexed or measured with `len`.
When the code under test treats its dependency like a list or dict, `MagicMock` is the double that supports those protocols out of the box.

**`patch` swaps reals for fakes, reversibly.**
The fifth block shows the most powerful piece.
`patch("...send_email")` replaces the real `send_email` with a mock *for the duration of the block*, so code that calls `send_email` gets the mock - and after the block, the real function is restored automatically.
This is how you test code that calls a dependency it does not receive as a parameter (a module-level function, a global service): you patch the name where it lives.
The automatic restore is essential - it means one test's patching cannot leak into another.

## The two-track note

There is no language mechanism here to defer to a Deep Volume; mocking is a testing technique assembled from the object model (attribute access, `__call__`, the dunder protocols) that the Deep Volumes cover.
What the timeline records is the release decision: in 3.3, the standard library absorbed the third-party `mock` library as `unittest.mock`, making test doubles a batteries-included tool.
The modern consequence, verified above, is that `Mock`, `MagicMock`, `patch`, `side_effect`, and the `assert_called_*` family are the standard vocabulary of Python unit testing, used directly and through `pytest`'s mocking integrations everywhere.

## Where this lands

`unittest.mock` is the tool that makes isolated unit testing practical in a language full of external dependencies.
Reach for a `Mock` to stand in for a collaborator and assert how it was called; `side_effect` to simulate failures and sequences; `MagicMock` when the double must support dunder protocols; and `patch` to swap a real object for a fake within a test and have it restored automatically.
Mock what your code *talks to*, not the code under test itself - and prefer passing collaborators as parameters (making them easy to substitute) over patching globals when you can.
No Deep Volume owns a testing mechanism; this chapter is the record of the release that made test doubles part of the standard library.
