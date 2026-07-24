"""Listing 14.2 - positional-only parameters give function authors the control
C builtins always had.

Before 3.8, a pure-Python function could not say "these parameters may be passed
only positionally." That mattered for two reasons. API stability: if a parameter
can be passed by keyword, its NAME becomes part of your public contract and you
can never rename it. **kwargs safety: a function like dict(**kwargs) could not
accept a key literally named as one of its parameters without a collision. The /
marker fixes both: every parameter before / is positional-only.
"""


def func(a, b, /, c, d, *, e, f):
    return (a, b, c, d, e, f)


co = func.__code__
print("--- the boundaries are encoded in the code object ---")
print("  co_posonlyargcount:", co.co_posonlyargcount, "(a, b before /)")
print("  co_argcount       :", co.co_argcount, "(a, b, c, d: all positionals)")
print("  co_kwonlyargcount :", co.co_kwonlyargcount, "(e, f after *)")

print()
print("--- calling within the contract works ---")
print("  func(1, 2, 3, 4, e=5, f=6):", func(1, 2, 3, 4, e=5, f=6))

print()
print("--- passing a positional-only param by keyword is a precise TypeError ---")
try:
    func(a=1, b=2, c=3, d=4, e=5, f=6)
except TypeError as exc:
    print("  func(a=1, b=2, ...) ->", str(exc))

print()
print("Mark a parameter positional-only when its name is an implementation")
print("detail you want freedom to rename, when you accept **kwargs that might")
print("collide with a parameter name, or when matching a builtin's signature.")
print("Do NOT reach for it in ordinary code where keyword arguments aid clarity;")
print("and, as the benchmark shows, not for speed.")
