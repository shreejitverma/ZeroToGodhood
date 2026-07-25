"""Listing 49.1 - inspect: rich, convenient, and expensive reflection.

inspect turns the raw introspection attributes (__code__, __dict__, __annotations__)
into a structured, uniform API: Signature/Parameter objects, type predicates
(isfunction, isclass), and source/member access. It is what frameworks use to
read a function's parameters for dependency injection, validation, or CLI
generation. That richness has a cost: building a Signature is far more work than
reading __code__ directly, so a hot path that reflects per call should CACHE the
result. This listing shows the API; the benchmark shows the cost.
"""

import inspect


def handler(user_id: int, name: str, active: bool = True, *tags, **opts) -> dict:
    return {}


def main() -> None:
    print("--- signature: parameters, kinds, defaults, annotations, as objects ---")
    sig = inspect.signature(handler)
    print(f"  str(signature)      : {sig}")
    for name, p in sig.parameters.items():
        default = "-" if p.default is inspect.Parameter.empty else repr(p.default)
        print(f"    {name:8} kind={p.kind.name:18} default={default}")
    print(f"  return annotation   : {sig.return_annotation.__name__}")

    print("--- type predicates: a uniform way to ask 'what is this?' ---")
    print(f"  isfunction(handler) : {inspect.isfunction(handler)}")
    print(f"  isclass(int)        : {inspect.isclass(int)}")
    print(f"  ismethod(handler)   : {inspect.ismethod(handler)}")
    print(f"  isbuiltin(len)      : {inspect.isbuiltin(len)}")

    print("--- binding arguments to parameters (what a framework does) ---")
    bound = sig.bind(42, "Ada")
    bound.apply_defaults()
    print(f"  bind(42, 'Ada')     : {dict(bound.arguments)}")

    print("--- the raw attributes inspect builds on (cheap, but unstructured) ---")
    print(f"  handler.__code__.co_varnames : {handler.__code__.co_varnames[:2]}...")
    print(f"  handler.__annotations__ keys : {sorted(handler.__annotations__)}")


if __name__ == "__main__":
    main()
