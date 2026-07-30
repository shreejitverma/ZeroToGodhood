"""Listing 191.1 - wheel tags: the compatibility claim, decoded and computed.

Chapter 109 said the wheel's filename is the compatibility claim. This listing
is the claim's grammar: `{name}-{version}-{python}-{abi}-{platform}.whl`,
three tags that answer three different questions (which interpreter may run
this? which C ABI does it bind? which OS and CPU?). It computes THIS
interpreter's own tags from first principles - which makes the output differ
across the verification matrix in exactly one block, because cp313, cp314,
and cp314t are three different ABIs, and that difference IS the tag system
working (Chapter 82 explained why the t-build needs its own wheels; this is
the machinery that enforces it).
"""

import sys
import sysconfig


EXAMPLES = [
    "requests-2.32.0-py3-none-any.whl",
    "numpy-2.1.0-cp313-cp313-macosx_14_0_arm64.whl",
    "cryptography-45.0.0-cp311-abi3-manylinux_2_28_x86_64.whl",
    "numpy-2.3.0-cp314-cp314t-macosx_14_0_arm64.whl",
]


def decode(filename):
    stem = filename.removesuffix(".whl")
    name, version, python, abi, platform = stem.split("-")
    return name, version, python, abi, platform


def this_interpreter_tag():
    tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
    if sysconfig.get_config_var("Py_GIL_DISABLED"):
        tag += "t"
    return tag


def acceptable_score(python, abi, mine):
    """0 = incompatible; higher = more specific compatible wheel."""
    if (python, abi) == ("py3", "none"):
        return 1                              # works, least specific
    if abi == "abi3" and python.startswith("cp"):
        floor = int(python.removeprefix("cp"))
        mine_num = int(mine.removeprefix("cp").removesuffix("t"))
        if not mine.endswith("t") and mine_num >= floor:
            return 2                          # stable ABI, forward-ok
    if python == abi == mine:
        return 3                              # exact ABI, most specific
    return 0


def main() -> None:
    print("--- the grammar: python tag - abi tag - platform tag ---")
    for filename in EXAMPLES:
        name, _, python, abi, platform = decode(filename)
        print(f"  {name:<12} python={python:<6} abi={abi:<6} platform={platform}")
    print("  py3-none-any : pure Python, no ABI, any OS - one wheel for the")
    print("    whole world (Chapter 109's tinypkg)")
    print("  cp313-cp313  : CPython 3.13's full ABI - one wheel PER minor")
    print("    version per platform (Chapter 82's flags, as a filename)")
    print("  cp311-abi3   : the stable ABI - built once against 3.11's limited")
    print("    API, installable on every CPython >= 3.11 (Chapter 82's trade)")
    print("  cp314-cp314t : the free-threaded ABI - a separate wheel universe,")
    print("    because Py_INCREF is compiled differently (Chapter 94)")

    print("--- this interpreter's own tags, computed ---")
    print(f"  interpreter/abi tag : {this_interpreter_tag()}")
    arch = sysconfig.get_platform().rsplit("-", 1)[-1]
    print(f"  platform arch       : {arch}")
    print("  (this block is the one that differs across the verification")
    print("   matrix, and that difference is the tag system doing its job)")

    print("--- how an installer chooses, in fifteen lines ---")
    acceptable = acceptable_score
    mine = this_interpreter_tag()
    candidates = [
        ("pkg-1.0-py3-none-any.whl", "py3", "none"),
        ("pkg-1.0-cp311-abi3-macosx_14_0_arm64.whl", "cp311", "abi3"),
        (f"pkg-1.0-{mine}-{mine}-macosx_14_0_arm64.whl", mine, mine),
    ]
    ranked = sorted(candidates, key=lambda c: acceptable(c[1], c[2], mine),
                    reverse=True)
    for filename, python, abi in ranked:
        score = acceptable(python, abi, mine)
        verdict = ["REJECT", "ok", "better", "best"][score]
        print(f"  {verdict:<7} {filename}")
    print("  most-specific compatible wheel wins: exact ABI over abi3 over")
    print("  pure Python, and everything else is rejected on the FILENAME,")
    print("  before any download - the cheap filter Chapter 109 promised")

    print("--- the abi3 asymmetry, stated ---")
    print("  a cp311-abi3 wheel installs on 3.11, 3.12, 3.13, 3.14... because")
    print("  the limited API freezes its symbols (Chapter 82); it does NOT")
    print("  install on any free-threaded build, whose ABI is disjoint - the")
    print("  one place the forward-compatibility story breaks today, and the")
    print("  adoption bottleneck Chapter 93 measured around")


if __name__ == "__main__":
    main()
