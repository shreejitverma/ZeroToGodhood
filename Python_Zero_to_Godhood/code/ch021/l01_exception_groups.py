"""Listing 21.1 - an ExceptionGroup carries many exceptions at once, and except*
routes them by type.

Before 3.11, an except clause caught one exception; if several things failed at
once (the natural case in concurrent code), you could propagate only one and the
rest were lost. PEP 654 added ExceptionGroup (a container of exceptions) and the
except* syntax, which matches the subgroup of a given type and lets the rest
propagate.
"""

# --- an ExceptionGroup is a container with a message and a list of exceptions ---
eg = ExceptionGroup(
    "multiple failures",
    [ValueError("bad value"), TypeError("bad type"), ValueError("another")],
)
print("--- the group object ---")
print("  type    :", type(eg).__name__)
print("  message :", eg.message)
print("  count   :", len(eg.exceptions))


def process():
    raise ExceptionGroup(
        "batch", [ValueError("v1"), TypeError("t1"), ValueError("v2"), KeyError("k1")]
    )


print()
print("--- except* matches the subgroup of each type; the rest propagate ---")
try:
    process()
except* ValueError as e:
    print("  except* ValueError ->", [str(x) for x in e.exceptions])
except* TypeError as e:
    print("  except* TypeError  ->", [str(x) for x in e.exceptions])
except* KeyError as e:
    print("  except* KeyError   ->", [str(x) for x in e.exceptions])

print()
print("--- split() is the programmatic form of except* ---")
matched, rest = eg.split(ValueError)
print("  eg.split(ValueError) -> matched:", len(matched.exceptions),
      "| rest:", len(rest.exceptions))
print()
print("ExceptionGroup subclasses BaseExceptionGroup, which can also hold")
print("BaseExceptions like KeyboardInterrupt; ExceptionGroup itself holds only")
print("ordinary Exceptions, so `except Exception` never accidentally swallows a")
print("shutdown signal buried in a group.")
