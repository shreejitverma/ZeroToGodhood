"""Listing 242.1 - Python 3.0 (2008): nonlocal, completing the closure.

Python 2 closures could READ a variable from an enclosing function but could not
REBIND it. Write `count = count + 1` in an inner function and Python treated
`count` as a NEW local, shadowing the outer one - so the outer never changed,
and you often got an UnboundLocalError. The workarounds were ugly: store the
value in a one-element list (`box[0] += 1`) to mutate through it, or promote it
to a global. Python 3.0's `nonlocal` keyword closes the gap: it declares that a
name refers to a variable in the nearest ENCLOSING function scope, so the inner
function can rebind it. This made the closure a complete tool - stateful inner
functions without a class or a list-in-a-box hack. Deep B owns the scope rules
(LEGB); this is the release that let inner functions write to their enclosing
scope. Verified on current interpreters.
"""


def make_counter():
    """A closure with mutable state - impossible to write cleanly before 3.0."""
    count = 0

    def increment():
        nonlocal count                           # rebind the ENCLOSING count
        count += 1
        return count

    return increment


def main() -> None:
    print("--- nonlocal lets an inner function REBIND an enclosing variable ---")
    counter = make_counter()
    print(f"  counter() : {counter()}")
    print(f"  counter() : {counter()}")
    print(f"  counter() : {counter()}")
    print("  each call rebinds the enclosing `count`. without nonlocal, `count")
    print("  += 1` would make count a new LOCAL and fail with UnboundLocalError")
    print("  (reading a local before it is assigned)")

    print("--- the exact failure nonlocal fixes ---")
    def broken():
        total = 0
        def add(n):
            total = total + n                    # NO nonlocal: total is local here
            return total
        try:
            return add(5)
        except UnboundLocalError as exc:
            return f"UnboundLocalError: {exc}"
    print(f"  inner reassigns without nonlocal : {broken()}")
    print("  `total = total + n` makes total a local of add(); reading it on the")
    print("  right-hand side before assignment raises. this is THE closure")
    print("  gotcha nonlocal was invented to remove")

    print("--- read vs rebind: reading never needed nonlocal ---")
    def outer():
        message = "hello"
        def reader():
            return message.upper()               # reading the enclosing var is fine
        def writer():
            nonlocal message                     # rebinding needs the declaration
            message = "changed"
        return reader, writer
    read, write = outer()
    print(f"  reader() before : {read()}")
    write()
    print(f"  reader() after writer() : {read()}")
    print("  reading an enclosing variable always worked (Python 2 too). only")
    print("  REBINDING needed a way to say 'this is the outer one, not a new")
    print("  local' - that is precisely what nonlocal declares")

    print("--- the pre-3.0 workaround nonlocal retired ---")
    def old_style_counter():
        box = [0]                                # mutate through a container
        def inc():
            box[0] += 1                          # no rebinding: mutate in place
            return box[0]
        return inc
    old = old_style_counter()
    print(f"  list-in-a-box counter : {old()}, {old()}, {old()}")
    print("  before nonlocal you wrapped state in a one-element list and mutated")
    print("  box[0] - never rebinding the name, only its contents. nonlocal")
    print("  makes the plain variable work, so the hack is gone")

    print("--- the constraint answered ---")
    print("  Python 2 closures could read but not rebind an enclosing variable,")
    print("  forcing list-in-a-box or global workarounds for stateful inner")
    print("  functions. nonlocal (3.0) declares 'this name is the enclosing")
    print("  one', so inner functions can update it directly - completing the")
    print("  closure as a first-class way to carry state")


if __name__ == "__main__":
    main()
