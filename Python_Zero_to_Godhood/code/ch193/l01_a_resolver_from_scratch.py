"""Listing 193.1 - dependency resolution: specifiers, backtracking, markers.

Chapter 111 ended with resolvers reading Requires-Dist without running
builds. This chapter is what they do with it, and as usual the mechanism is
shown by building it: a version-specifier evaluator, an environment-marker
evaluator, and a complete backtracking resolver in ~40 lines, run against a
tiny package universe twice - once to a solution (watch it backtrack out of a
wrong choice), once into a provable conflict (watch it name the culprits).

The trace is deterministic because the strategy is: try newest first, depth
first, backtrack on contradiction. Real resolvers add caching, heuristics,
and error prose; the SHAPE - and the exponential worst case the benchmark
measures - is exactly this.
"""

import sys


def parse(v):
    return tuple(int(part) for part in v.split("."))


def satisfies(version, spec):
    """A working core of PEP 440: >=, <, ==, != over dotted versions."""
    if not spec:
        return True
    for clause in spec.split(","):
        op = clause.rstrip("0123456789.")
        bound = parse(clause[len(op):])
        v = parse(version)
        ok = {">=": v >= bound, "<": v < bound,
              "==": v == bound, "!=": v != bound}[op]
        if not ok:
            return False
    return True


def evaluate_marker(marker):
    """A working core of PEP 508 markers against the running environment."""
    if not marker:
        return True
    env = {
        "python_version": f"{sys.version_info.major}.{sys.version_info.minor}",
        "sys_platform": sys.platform,
    }
    name, op, _, value = marker.split(" ", 3)
    left, right = env[name], value.strip('"')
    if name == "python_version":
        left, right = parse(left), parse(right)
    return {">=": left >= right, "==": left == right}[op]


def resolve(universe, requirements, trace):
    """Depth-first, newest-first, backtracking. Returns pins or None."""

    def attempt(pins, todo):
        if not todo:
            return pins
        name, spec = todo[0]
        if name in pins:
            if satisfies(pins[name], spec):
                return attempt(pins, todo[1:])
            trace.append(f"conflict: {name}=={pins[name]} fails {spec!r}")
            return None
        for version in sorted(universe[name], key=parse, reverse=True):
            if not satisfies(version, spec):
                continue
            trace.append(f"try {name}=={version}")
            deps = [(d, s) for d, s, marker in universe[name][version]
                    if evaluate_marker(marker)]
            solution = attempt({**pins, name: version}, todo[1:] + deps)
            if solution is not None:
                return solution
            trace.append(f"backtrack from {name}=={version}")
        return None

    return attempt({}, list(requirements))


def main() -> None:
    print("--- specifiers, evaluated ---")
    for version, spec in (("1.9.0", ">=1.5,<2.0"), ("2.0.0", ">=1.5,<2.0"),
                          ("1.4.2", "!=1.4.2")):
        print(f"  {version} satisfies {spec!r:<14} : {satisfies(version, spec)}")

    print("--- markers, evaluated against THIS environment ---")
    for marker in ('python_version >= _ "3.11"', 'sys_platform == _ "darwin"'):
        pretty = marker.replace(" _ ", " ")
        print(f"  {pretty:<28} : {evaluate_marker(marker)}")
    print("  markers make one metadata file serve every environment: the")
    print("  dependency exists only where its marker is true (and the same")
    print("  mechanism guards python_version floors and OS-specific deps)")

    universe = {
        "app": {"1.0.0": [("web", ">=2.0", ""), ("db", ">=1.0", "")]},
        "web": {"3.0.0": [("codec", ">=2.0", "")],
                "2.5.0": [("codec", ">=1.0,<2.0", "")]},
        "db": {"1.2.0": [("codec", "<2.0", "")]},
        "codec": {"2.1.0": [], "1.8.0": []},
    }

    print("--- the solve, traced: newest first, backtrack on contradiction ---")
    trace: list[str] = []
    pins = resolve(universe, [("app", ">=1.0")], trace)
    for line in trace:
        print(f"    {line}")
    print(f"  solution : {dict(sorted(pins.items()))}")
    print("  web 3.0 was tried first (newest) and DROPPED: its codec>=2.0")
    print("  contradicts db's codec<2.0, so the resolver backtracked to")
    print("  web 2.5. a pin is not a preference; it is a survivor")

    print("--- an honest conflict, named ---")
    universe["db"]["1.2.0"] = [("codec", "<2.0", "")]
    universe["web"].pop("2.5.0")          # now only web 3.0 exists
    trace.clear()
    pins = resolve(universe, [("app", ">=1.0")], trace)
    for line in trace:
        print(f"    {line}")
    print(f"  solution : {pins}")
    print("  no assignment satisfies codec>=2.0 AND codec<2.0: the resolver")
    print("  proved it by exhausting the space, which is why real conflict")
    print("  messages list a CHAIN of requirements - that chain is the proof")


if __name__ == "__main__":
    main()
