"""Listing 112.2 - __format__, and the f-string conversion flags.

f-strings and format() route through a THIRD method, __format__(self, spec), which
receives the format specification after the colon (f"{x:spec}"). It defaults to
__str__ for an empty spec. The conversion flags force a specific method, bypassing
__format__:
  f"{x}"   -> x.__format__("")   (defaults to str)
  f"{x!s}" -> str(x)             (force __str__)
  f"{x!r}" -> repr(x)            (force __repr__)
  f"{x!a}" -> ascii(x)           (force __repr__, then escape non-ASCII)
This listing shows the three methods and a __format__ that honours a spec.
"""


class Both:
    def __repr__(self):
        return "Both(repr)"

    def __str__(self):
        return "Both(str)"


class Temperature:
    def __init__(self, celsius):
        self.celsius = celsius

    def __format__(self, spec):
        if spec == "f":                  # Fahrenheit, when asked
            return f"{self.celsius * 9 / 5 + 32:.1f}F"
        return f"{self.celsius:.1f}C"    # Celsius by default


def main() -> None:
    b = Both()

    print("--- conversion flags pick the method ---")
    print(f"  f'{{b}}'   (default/__format__ -> __str__) : {b}")
    print(f"  f'{{b!s}}' (force str)  : {b!s}")
    print(f"  f'{{b!r}}' (force repr) : {b!r}")

    print("--- __format__ receives the spec after the colon ---")
    t = Temperature(20.0)
    print(f"  f'{{t}}'    (empty spec) : {t}")
    print(f"  f'{{t:f}}'  (spec 'f')   : {t:f}")

    print("--- format() is the same protocol without an f-string ---")
    print(f"  format(t, 'f') : {format(t, 'f')}")

    print("--- the rule ---")
    print(f"  f'{{x}}' and format() call __format__ (defaults to __str__); !s/!r/!a")
    print(f"  force str/repr/ascii; a format spec after ':' is passed to __format__")


if __name__ == "__main__":
    main()
