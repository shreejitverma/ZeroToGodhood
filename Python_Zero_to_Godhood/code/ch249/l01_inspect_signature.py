"""Listing 249.1 - Python 3.3 (2012): inspect.signature, callables that describe themselves.

Frameworks constantly need to ask a function 'what parameters do you take?' - to
inject dependencies, validate a call, build a CLI or an API schema. Before 3.3
the answer lived in inspect.getfullargspec, which returned a bundle of parallel
lists (args, defaults, varargs, ...) that you had to reassemble by hand, and it
did not model keyword-only arguments or the newer parameter kinds well. Python
3.3's PEP 362 added inspect.signature: a single Signature object with an ordered
mapping of Parameter objects, each knowing its name, KIND, and default. It is
the introspection layer every modern framework (dataclasses, pydantic, click,
pytest fixtures) is built on. Deep C owns the callable/descriptor model; this is
the release that gave callables a clean, object-based self-description. Verified
on current interpreters.
"""

import inspect


def handler(path, method="GET", *middlewares, timeout=30, **options):
    ...


def main() -> None:
    print("--- signature() gives one object that renders the whole signature ---")
    sig = inspect.signature(handler)
    print(f"  str(signature(handler)) : {sig}")
    print("  one call, one object - it prints the signature as written. no")
    print("  reassembling parallel lists of args/defaults/varargs by hand")

    print("--- each parameter knows its name, KIND, and default ---")
    for name, param in sig.parameters.items():
        default = "-" if param.default is inspect.Parameter.empty else param.default
        print(f"  {name:<12} kind={param.kind.name:<20} default={default}")
    print("  the five KINDS distinguish positional-or-keyword, *args")
    print("  (VAR_POSITIONAL), keyword-only, and **kwargs (VAR_KEYWORD) - the")
    print("  full argument model of Chapter 243, as inspectable objects")

    print("--- bind(): match arguments to parameters, like a call would ---")
    bound = sig.bind("/users", "POST", timeout=5)
    bound.apply_defaults()
    print(f"  bind('/users', 'POST', timeout=5).arguments :")
    for k, v in bound.arguments.items():
        print(f"    {k} = {v}")
    print("  bind() applies the SAME matching rules a real call uses, so a")
    print("  framework can resolve what each parameter WOULD receive - the")
    print("  basis of dependency injection and request routing")

    print("--- bind() enforces the signature: a bad call is caught ---")
    try:
        sig.bind()                               # 'path' is required
    except TypeError as exc:
        print(f"  bind() with no args -> TypeError: {exc}")
    print("  bind() raises exactly as calling the function would, so validation")
    print("  can happen BEFORE the call, from the signature alone")

    print("--- it introspects builtins and methods too, uniformly ---")
    print(f"  signature(len)            : {inspect.signature(len)}")
    print(f"  signature(dict.get)       : {inspect.signature(dict.get)}")
    print("  the same Signature object describes user functions, builtins, and")
    print("  methods, so introspection code does not special-case callable kinds")

    print("--- the constraint answered ---")
    print("  callables could be introspected only via getfullargspec's parallel")
    print("  lists, awkward and blind to keyword-only args. signature() (3.3)")
    print("  gave one Signature object with ordered, self-describing Parameter")
    print("  objects and a bind() that mirrors real calls. every modern")
    print("  framework's parameter handling stands on it")


if __name__ == "__main__":
    main()
