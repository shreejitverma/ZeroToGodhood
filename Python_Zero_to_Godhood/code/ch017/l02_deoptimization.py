"""Listing 17.2 - a polymorphic call site cannot hold one specialization.

Specialization is a bet on monomorphism: that a given site sees the same type run
after run. This is clearest with two types whose attribute access needs different
fast paths: a __slots__ class (LOAD_ATTR_SLOT, a fixed-offset read) and an
ordinary class (LOAD_ATTR_INSTANCE_VALUE, an instance-values read). A site that
sees only one specializes to that path; a site that sees both cannot, and its
guard misses on every call to the other type, deoptimizing.

The disassembly shows which specialization a site settled on; the RUNTIME cost of
the guard misses at a polymorphic site is what the chapter's benchmark measures.
"""

import dis


class Slotted:
    __slots__ = ("x",)

    def __init__(self):
        self.x = 1


class Dicted:
    def __init__(self):
        self.x = 2


def read_mono(o):
    return o.x


def read_poly(o):
    return o.x


s, d = Slotted(), Dicted()

for _ in range(1000):                 # monomorphic: only Slotted
    read_mono(s)

for i in range(1000):                 # polymorphic: alternating Slotted and Dicted
    read_poly(s if i % 2 else d)

mono_op = [i.opname for i in dis.get_instructions(read_mono, adaptive=True)
           if i.opname.startswith("LOAD_ATTR")]
poly_op = [i.opname for i in dis.get_instructions(read_poly, adaptive=True)
           if i.opname.startswith("LOAD_ATTR")]

print("--- the same code, monomorphic vs polymorphic call site ---")
print("  read_mono (Slotted only) LOAD_ATTR:", mono_op)
print("  read_poly (Slotted+Dicted) LOAD_ATTR:", poly_op)
print()
print("The monomorphic site holds LOAD_ATTR_SLOT, the fast fixed-offset read for")
print("a __slots__ class. The polymorphic site settled on")
print("LOAD_ATTR_INSTANCE_VALUE (the ordinary-class path), whose guard then MISSES")
print("on every Slotted instance and deoptimizes, so half its calls run the")
print("generic slow path. Keep hot call sites monomorphic; do not mutate classes")
print("at runtime (it bumps tp_version_tag and invalidates every dependent cache).")
