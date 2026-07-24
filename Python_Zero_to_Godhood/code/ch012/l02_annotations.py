"""Listing 12.2 - annotations are metadata, and where they are stored depends on
scope.

The interpreter never type-checks an annotation. At module or class scope the
compiler emits SETUP_ANNOTATIONS and records each in an __annotations__ dict,
introspectable at runtime. At function-local scope the annotation is discarded
entirely: no storage, zero runtime cost, because locals are executed on hot
paths.
"""

import dis


class Profile:
    name: str = "Anon"
    age: int                      # annotation only, no value


print("--- class annotations are stored in __annotations__ ---")
print("  Profile.__annotations__:", Profile.__annotations__)


def process():
    y: int = 42                   # the ': int' is discarded by the compiler
    return y


print()
print("--- function-local annotations leave no trace in the bytecode ---")
ops = [i.opname for i in dis.get_instructions(process)
       if i.opname in ("LOAD_CONST", "STORE_FAST", "LOAD_FAST", "SETUP_ANNOTATIONS",
                       "LOAD_SMALL_INT", "RETURN_VALUE")]
print("  process() opcodes:", ops)
print("  no SETUP_ANNOTATIONS: the ': int' cost nothing.")
print()
print("Annotations are NOT runtime validation: x: int = 'nope' runs fine.")
print("For enforcement use pydantic, dataclass validators, or a runtime checker.")
