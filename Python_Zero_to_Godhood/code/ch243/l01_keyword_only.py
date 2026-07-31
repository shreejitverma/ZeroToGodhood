"""Listing 243.1 - Python 3.0 (2008): keyword-only arguments, call sites that read.

A function like connect(host, 5, True, False) is unreadable: what are 5, True,
False? Positional arguments let callers pass options by position, so boolean
flags and tuning knobs become mystery values at the call site. Python 3.0's
PEP 3102 added keyword-only parameters: a bare `*` in the signature means every
parameter after it MUST be passed by name. connect(host, timeout=5,
retry=True, verbose=False) is forced, and now it reads. This is an API-design
tool - it lets a function author REQUIRE that options be named, so calls stay
self-documenting and adding a new option never shifts a positional meaning.
Deep B owns the call/argument-binding model; this is the release that let a
signature demand named arguments. Verified on current interpreters.
"""


def connect(host, *, timeout=30, retry=False, verbose=False):
    """Everything after * is keyword-only: it MUST be passed by name."""
    return f"{host} timeout={timeout} retry={retry} verbose={verbose}"


def main() -> None:
    print("--- a bare * makes every following parameter keyword-only ---")
    print(f"  connect('db', timeout=5, retry=True) ->")
    print(f"    {connect('db', timeout=5, retry=True)}")
    print("  host is positional; timeout/retry/verbose come after `*`, so they")
    print("  MUST be named. the call spells out what each option is - no bare")
    print("  5/True/False whose meaning you have to look up")

    print("--- passing a keyword-only argument positionally is an ERROR ---")
    try:
        connect("db", 5)                         # tries to pass 5 to timeout positionally
    except TypeError as exc:
        print(f"  connect('db', 5) -> TypeError: {exc}")
    print("  the function AUTHOR decided timeout cannot be positional. the")
    print("  unreadable connect('db', 5, True, False) is now impossible to")
    print("  write - the signature forbids it, not just discourages it")

    print("--- the readability contrast, side by side ---")
    print("  positional (hypothetical) : connect('db', 5, True, False)")
    print("  keyword-only (enforced)   : connect('db', timeout=5, retry=True,")
    print("                                      verbose=False)")
    print("  same information; the second is self-documenting. keyword-only")
    print("  arguments make the readable form the ONLY form")

    print("--- *args also opens keyword-only: params after *args are named ---")
    def log(level, *messages, sep=" ", upper=False):
        text = sep.join(messages)
        return f"[{level}] {text.upper() if upper else text}"
    print(f"  log('INFO', 'a', 'b', 'c') : {log('INFO', 'a', 'b', 'c')}")
    print(f"  log('WARN', 'x', 'y', sep='-', upper=True) : "
          f"{log('WARN', 'x', 'y', sep='-', upper=True)}")
    print("  when a function takes *messages (any number of positionals), sep")
    print("  and upper come AFTER it, so they are automatically keyword-only -")
    print("  there is no positional slot left for them. options stay named")

    print("--- why it matters for API evolution ---")
    print("  because options are named, the author can ADD a new keyword-only")
    print("  parameter without breaking any existing call: no caller was")
    print("  relying on positional order for those options. positional params,")
    print("  by contrast, freeze their order into every call site forever")

    print("--- the constraint answered ---")
    print("  positional arguments let options be passed as bare values, making")
    print("  call sites unreadable and positional order a compatibility trap.")
    print("  keyword-only parameters (3.0) let a signature REQUIRE that options")
    print("  be named, so calls document themselves and new options can be")
    print("  added safely. the signature became an API-design tool")


if __name__ == "__main__":
    main()
