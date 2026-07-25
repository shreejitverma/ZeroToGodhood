"""Listing 42.1 - json vs pickle: the trade is safety and interop, not speed.

json is text, universal (every language reads it), and encodes only data: dict,
list, str, int, float, bool, None. pickle is binary, Python-only, and encodes
almost any Python object, but it is a code-execution format: unpickling runs
whatever the pickle's __reduce__ says, so loading an untrusted pickle is remote
code execution. This listing shows the type-coverage difference and, safely, the
mechanism that makes pickle dangerous. The benchmark shows pickle is actually the
faster and smaller of the two, so speed is not the reason to prefer json.
"""

import builtins
import json
import pickle


class Exploit:
    """A stand-in for a malicious pickle. __reduce__ decides what runs on load."""

    def __reduce__(self):
        # On pickle.loads this is invoked as print(...): code runs during load.
        return (builtins.print, ("      [!] code executed during unpickle",))


def main() -> None:
    print("--- type coverage: json is data-only; pickle takes most objects ---")
    data = {"name": "Ada", "tags": ["a", "b"], "count": 3}
    print(f"  json round-trip     : {json.loads(json.dumps(data))}")
    # a set is not JSON-serializable; pickle handles it
    s = {1, 2, 3}
    try:
        json.dumps(s)
    except TypeError as e:
        print(f"  json.dumps(set)     : TypeError ({e})")
    print(f"  pickle round-trip set: {pickle.loads(pickle.dumps(s))}")

    print("--- the security difference: unpickling runs code ---")
    payload = pickle.dumps(Exploit())     # an attacker-controlled byte string
    print("  pickle.loads(untrusted):")
    pickle.loads(payload)                 # prints the injected message: code ran
    print("  json.loads never runs code: it only ever produces data")

    print("--- json is human-readable text; pickle is opaque binary ---")
    print(f"  json.dumps(data)    : {json.dumps(data)}")
    blob = pickle.dumps(data)
    # first byte is the PROTO opcode 0x80 (same in every protocol >= 2);
    # the following protocol-number byte is version-dependent, so we do not show it
    print(f"  pickle is bytes     : starts with {blob[:1]!r} (PROTO opcode), {len(blob)} bytes total")


if __name__ == "__main__":
    main()
