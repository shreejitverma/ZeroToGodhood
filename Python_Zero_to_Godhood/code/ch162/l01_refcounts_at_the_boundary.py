"""Listing 162.1 - reference counting across the C boundary: owned, borrowed, leaked.

Every PyObject* that crosses into C carries an obligation, and the C-API's whole
discipline is which side owns it:

  OWNED    - the C function received (or created) a reference and must eventually
             Py_DECREF it. Failing to is a LEAK.
  BORROWED - the C function may use the pointer while the caller's reference is alive,
             and must NOT decref it. Decref'ing a borrowed reference is a premature
             free, which is a use-after-free for whoever still holds it.

Python code never sees this, because the interpreter balances every reference it takes.
The moment a C extension, or ctypes, is in the picture, the balance becomes the
programmer's job, and both directions of imbalance are silent until they are fatal.

This listing makes all of it observable from Python by calling CPython's own Py_IncRef
and Py_DecRef through ctypes.pythonapi. It shows the counting, the +1 artifact of
sys.getrefcount, the recovery of an object from a raw address, immortal objects (PEP
683) whose count does not move, an actual staged leak, and the keep-alive graph ctypes
maintains in `_objects` so that a pointer it hands to C cannot outlive its buffer.
"""

import ctypes
import gc
import sys
import weakref

API = ctypes.pythonapi
API.Py_IncRef.argtypes = [ctypes.py_object]
API.Py_IncRef.restype = None
API.Py_DecRef.argtypes = [ctypes.py_object]
API.Py_DecRef.restype = None


class Probe:
    """A plain object with no __slots__ and no finalizer, so nothing else holds it."""


def incref_delta(obj):
    """How much an explicit Py_IncRef moves the count. 0 means the object is immortal."""
    before = sys.getrefcount(obj)
    API.Py_IncRef(obj)
    during = sys.getrefcount(obj)
    API.Py_DecRef(obj)
    return during - before


GLOBAL_PROBE = Probe()


def main() -> None:
    held = Probe()
    boxed = [Probe()]

    # This block differs between 3.13.5 and 3.14.6, and the difference is the chapter's
    # subject arriving early: 3.14 reads a local with LOAD_FAST_BORROW, so passing a
    # LOCAL to getrefcount no longer creates a reference. Reading the same object from
    # a global or out of a list still does.
    print("--- what does sys.getrefcount count? (the local row is version-dependent) ---")
    print(f"  a local name             : {sys.getrefcount(held)}")
    print(f"  a module global          : {sys.getrefcount(GLOBAL_PROBE)}")
    print(f"  an item read from a list : {sys.getrefcount(boxed[0])}")

    print("--- so read DELTAS, not absolute counts: those are version-stable ---")
    before = sys.getrefcount(held)
    API.Py_IncRef(held)
    during = sys.getrefcount(held)
    API.Py_DecRef(held)
    after = sys.getrefcount(held)
    print(f"  one Py_IncRef moves the count by : {during - before}")
    print(f"  IncRef then DecRef is balanced   : {before == after}")
    print(f"  getrefcount(a temporary)         : {sys.getrefcount(Probe())}   (the argument alone)")

    print("--- a PyObject* is just an address; id() is that address ---")
    recovered = ctypes.cast(id(held), ctypes.py_object).value
    print(f"  cast(id(obj), py_object).value is obj : {recovered is held}")

    print("--- immortal objects (PEP 683): the count does not move ---")
    print(f"  a fresh list : delta {incref_delta([1, 2, 3])}   (ordinary, mortal)")
    for immortal in (None, True, 5, "spam"):
        print(f"  {immortal!r:<12} : delta {incref_delta(immortal)}   (immortal)")

    print("--- a leak, staged: one IncRef that nothing balances ---")
    victim = Probe()
    watch = weakref.ref(victim)
    API.Py_IncRef(victim)                 # what a C function that forgot DECREF does
    del victim
    gc.collect()
    print(f"  alive after del and a full gc.collect() : {watch() is not None}")
    print("  (no cycle is involved, so the collector cannot help: the count is simply wrong)")

    leaked = watch()
    API.Py_DecRef(leaked)                 # supply the missing decref
    del leaked
    gc.collect()
    print(f"  alive after the missing DecRef is supplied : {watch() is not None}")

    print("--- ctypes tracks keep-alive edges so a pointer cannot outlive its buffer ---")
    buffer = ctypes.create_string_buffer(b"hello")
    pointer = ctypes.cast(buffer, ctypes.c_char_p)
    print(f"  cast(buffer, c_char_p)._objects is set : {pointer._objects is not None}")
    backing = bytearray(b"abcd")
    view = (ctypes.c_char * 4).from_buffer(backing)
    print(f"  from_buffer(bytearray)._objects is set : {view._objects is not None}")
    print(f"  writing through it reaches the bytearray : {bytes(backing)!r} -> ", end="")
    view[0] = b"A"
    print(f"{bytes(backing)!r}")
    del view                              # release the export before the bytearray grows
    backing.append(ord("!"))
    print(f"  bytearray grows once the export is gone : {bytes(backing)!r}")

    print("--- the rule ---")
    print("  every reference that crosses into C is either owned (you must decref it) or")
    print("  borrowed (you must not); too few decrefs leak, too many free memory in use")


if __name__ == "__main__":
    main()
