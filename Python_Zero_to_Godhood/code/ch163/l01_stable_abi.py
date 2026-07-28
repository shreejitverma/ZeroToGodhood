"""Listing 163.1 - why a compiled extension names a Python version, and how to avoid it.

A C extension is a shared library that was compiled against CPython's headers. Those
headers describe struct LAYOUTS - how many bytes into a PyObject the refcount sits, how
big PyTypeObject is - and CPython changes those layouts between feature releases. A
library compiled against 3.13's layouts and loaded into 3.14 would read the wrong
offsets, so the import machinery refuses to try: the file name carries the version, and
only the matching interpreter looks for it.

That is the DEFAULT contract, and it is the reason a project shipping wheels must build
one per Python version per platform.

The LIMITED API (PEP 384) is the opt-out. Compiling with Py_LIMITED_API restricts the
extension to a subset of the C-API whose layouts and signatures are frozen, in exchange
for a single binary - tagged `.abi3.so` - that loads into every version from the one you
targeted onward. The STABLE ABI is the guarantee; the limited API is the subset you must
stay inside to earn it.

This listing reports the structure of that contract rather than its version-specific
values, so the output is identical on both verification interpreters. The values
themselves (SOABI, EXT_SUFFIX) are version tags by construction, and printing them would
only prove that they differ.
"""

import importlib.machinery
import sys
import sysconfig

# A few versions an extension might target with Py_LIMITED_API. The constant is a hex
# version: 0x030A0000 means "3.10 and later".
LIMITED_API_TARGETS = (0x03020000, 0x030A0000, 0x030D0000, 0x03140000)


def decode_limited_api(value):
    """Py_LIMITED_API is a packed hex version: 0xMMmm0000."""
    return (value >> 24) & 0xFF, (value >> 16) & 0xFF


def main() -> None:
    suffixes = importlib.machinery.EXTENSION_SUFFIXES
    tagged = sysconfig.get_config_var("EXT_SUFFIX")
    soabi = sysconfig.get_config_var("SOABI")
    major, minor = sys.version_info[:2]

    print("--- the import machinery accepts three shapes of extension filename ---")
    print(f"  how many suffixes are searched : {len(suffixes)}")
    print(f"  one is version-tagged          : {any('cpython-' in s for s in suffixes)}")
    print(f"  one is the stable-ABI tag      : {'.abi3.so' in suffixes or '.abi3.pyd' in suffixes}")
    print(f"  one is the bare extension      : {suffixes[-1] in ('.so', '.pyd')}")
    print(f"  the version-tagged one is tried first : {suffixes[0] == tagged}")

    print("--- the version tag is this interpreter's version, spelled into the filename ---")
    print(f"  EXT_SUFFIX names this version : {f'{major}{minor}' in (tagged or '')}")
    print(f"  SOABI names this version      : {f'{major}{minor}' in (soabi or '')}")
    print(f"  the abi3 tag names NO version : "
          f"{not any(ch.isdigit() for ch in '.abi3.so'.replace('abi3', ''))}")

    print("--- build variants get their own tag, so they cannot load each other's .so ---")
    print(f"  this is a debug build          : {bool(sysconfig.get_config_var('Py_DEBUG'))}")
    print(f"  this is a free-threaded build  : {bool(sysconfig.get_config_var('Py_GIL_DISABLED'))}")
    print(f"  abiflags (empty on a release, GIL-enabled build) : {sys.abiflags!r}")

    print("--- Py_LIMITED_API is a packed hex minimum: does this interpreter satisfy it? ---")
    for target in LIMITED_API_TARGETS:
        want = decode_limited_api(target)
        loadable = sys.version_info[:2] >= want
        print(f"  declares >= {want[0]}.{want[1]:<3} (0x{target:08X}) : satisfied here = {loadable}")

    print("--- the trade, stated as a table ---")
    print("  default C-API : full API, struct layouts visible, one wheel PER VERSION")
    print("  limited API   : frozen subset, layouts opaque, ONE wheel for 3.x and later")

    print("--- the rule ---")
    print("  a version-tagged .so is a promise you will rebuild every release; an")
    print("  .abi3.so is a promise you stayed inside the frozen subset")


if __name__ == "__main__":
    main()
