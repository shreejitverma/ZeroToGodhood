"""Listing 156.1 - the three name-lookup paths, and why they cost different amounts.

A name read in a function body is resolved by ONE of three mechanisms, chosen by the
compiler, not at runtime:

  local   -> an ARRAY SLOT in the frame (LOAD_FAST family). No hashing, no dict.
  global  -> a DICT probe in the module's globals (LOAD_GLOBAL).
  builtin -> the SAME LOAD_GLOBAL, which misses globals and then probes builtins.

The compiler decides from the function's syntax alone: a name assigned anywhere in the
body is local EVERYWHERE in the body; otherwise it is global/builtin. That decision is
frozen into co_varnames (indexed locals) and co_names (names looked up by string). This
listing shows the per-name classification, the hoisting idiom that turns a global lookup
into a local one, and the UnboundLocalError the compile-time rule produces.

Opcode names are collapsed to FAMILIES because 3.14 renamed LOAD_FAST to
LOAD_FAST_BORROW at most read sites (see the chapter's edges section). The mechanism -
array slot versus dict probe - is what the listing is about, and that is stable.
"""

import builtins
import dis

MODULE_LEVEL = 7


def uses_local(n):
    total = 0                             # assigned -> local -> array slot
    for i in range(n):
        total = total + i
    return total


def uses_global(n):
    return n * MODULE_LEVEL               # never assigned here -> globals dict probe


def uses_builtin(xs):
    return len(xs)                        # not local, not in globals -> builtins


def hoisted(xs):
    _len = len                            # bind the builtin to a LOCAL, once
    total = 0
    for x in xs:
        total = total + _len(x)           # every use is now an array slot
    return total


def looks_global_but_is_not():
    """MODULE_LEVEL is assigned below, so it is local on EVERY line, including the read."""
    print(MODULE_LEVEL)                   # UnboundLocalError: the slot is still empty
    MODULE_LEVEL = 1


FAMILY = {
    "LOAD_FAST": "LOAD_FAST*  (array slot)",
    "LOAD_GLOBAL": "LOAD_GLOBAL (dict probe)",
    "LOAD_DEREF": "LOAD_DEREF  (closure cell)",
}


def reads(ins, name):
    """Does this instruction name `name`? Superinstructions carry a tuple of names."""
    if isinstance(ins.argval, tuple):
        return name in ins.argval
    return ins.argval == name


def mechanism(fn, name):
    """Which opcode family reads `name` inside `fn`, collapsed across the 3.14 rename."""
    for ins in dis.get_instructions(fn):
        if not reads(ins, name):
            continue
        for prefix, label in FAMILY.items():
            if ins.opname.startswith(prefix):
                return label
    return "not read"


def main() -> None:
    print("--- the compiler picks the mechanism per NAME, at compile time ---")
    for fn, name in (
        (uses_local, "total"),
        (uses_local, "range"),
        (uses_global, "MODULE_LEVEL"),
        (uses_builtin, "len"),
        (hoisted, "_len"),
    ):
        print(f"  {fn.__name__ + '.' + name:<26} {mechanism(fn, name)}")

    print("--- co_varnames is the indexed array; co_names is probed by string ---")
    print(f"  uses_local.co_varnames  : {uses_local.__code__.co_varnames}")
    print(f"  uses_local.co_names     : {uses_local.__code__.co_names}")
    print(f"  uses_global.co_varnames : {uses_global.__code__.co_varnames}")
    print(f"  uses_global.co_names    : {uses_global.__code__.co_names}")

    print("--- a builtin is not a separate opcode: LOAD_GLOBAL misses, then probes builtins ---")
    print(f"  uses_builtin.co_names   : {uses_builtin.__code__.co_names}")
    print(f"  'len' in module globals : {'len' in globals()}")
    print(f"  'len' in builtins       : {'len' in vars(builtins)}")

    print("--- hoisting: bind it to a local once, then index the array ---")
    print(f"  hoisted.co_varnames     : {hoisted.__code__.co_varnames}")
    print(f"  hoisted.co_names        : {hoisted.__code__.co_names}")
    print(f"  hoisted(['ab', 'cde'])  : {hoisted(['ab', 'cde'])}")

    print("--- the rule has teeth: assignment anywhere makes the name local everywhere ---")
    print(f"  MODULE_LEVEL at module scope        : {MODULE_LEVEL}")
    print(f"  looks_global_but_is_not.co_varnames : {looks_global_but_is_not.__code__.co_varnames}")
    try:
        looks_global_but_is_not()
    except UnboundLocalError as exc:
        print(f"  calling it raises                   : {type(exc).__name__}")

    print("--- the rule ---")
    print("  locals are array slots; globals and builtins are dict probes (two, for a")
    print("  builtin). In a hot loop, hoist the name you read repeatedly into a local")


if __name__ == "__main__":
    main()
