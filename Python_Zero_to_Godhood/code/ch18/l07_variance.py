"""Listing 18.7 - variance stops being something you declare.

Under the legacy spelling you told the checker whether a parameter was
covariant, and you were on your own if you got it wrong. A PEP 695 type
parameter is created with `infer_variance=True`, which moves the decision to
the type checker, where the information actually is.

The runtime does not enforce variance either way. This flag is a message to
the checker, and this listing shows the message being set, not obeyed.
"""

from typing import TypeVar

legacy_co = TypeVar("LegacyCo", covariant=True)
legacy_contra = TypeVar("LegacyContra", contravariant=True)
legacy_plain = TypeVar("LegacyPlain")


def modern[T](x: T) -> T:
    return x


(modern_t,) = modern.__type_params__

rows = [
    ("TypeVar('LegacyCo', covariant=True)", legacy_co),
    ("TypeVar('LegacyContra', contravariant=True)", legacy_contra),
    ("TypeVar('LegacyPlain')", legacy_plain),
    ("PEP 695  def modern[T]", modern_t),
]

print(f"{'spelling':46} {'co':>6} {'contra':>7} {'infer':>6}")
print("-" * 68)
for label, tv in rows:
    print(f"{label:46} {tv.__covariant__!s:>6} "
          f"{tv.__contravariant__!s:>7} {tv.__infer_variance__!s:>6}")

print()
print("--- bounds and constraints are lazy too ---")


def bounded[T: Undefined](x: T) -> T:
    return x


(bt,) = bounded.__type_params__
print("the bound referenced an undefined name; definition still succeeded")
try:
    bt.__bound__
except NameError as exc:
    print("accessing __bound__ ->", type(exc).__name__ + ":", exc)

print()
print("--- constrained type parameters use a tuple, and are also lazy ---")


def constrained[T: (int, str)](x: T) -> T:
    return x


(ct,) = constrained.__type_params__
print("constraints =", ct.__constraints__)
print("bound       =", ct.__bound__)
