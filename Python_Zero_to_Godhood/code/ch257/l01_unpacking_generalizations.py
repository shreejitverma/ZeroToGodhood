"""Listing 257.1 - Python 3.5 (2015): PEP 448, * and ** unpacking generalized.

Chapter 244 showed * on the LEFT of an assignment (first, *rest = seq). PEP 448
extended * and ** to the places that had lacked them: inside list/set/dict/tuple
LITERALS and in function CALLS with multiple unpackings. Before 3.5, merging two
lists into a new one meant a + b or list(a) + list(b); merging two dicts meant a
dict copy then update; calling f with args from two sources needed itertools or
a temporary. After 3.5, [*a, *b], {**d1, **d2}, and f(*a, *b, **kw) say it
directly. It made 'combine these into a new collection' a literal, not a
procedure. Deep B owns the call and display grammar; this is the release that let
unpacking appear wherever a collection is built. Verified on current interpreters.
"""


def main() -> None:
    print("--- * inside a list/tuple/set literal merges iterables ---")
    a = [1, 2, 3]
    b = [4, 5]
    merged = [*a, *b]
    print(f"  [*a, *b] : {merged}")
    print(f"  [0, *a, 99, *b] (interleave with literals) : {[0, *a, 99, *b]}")
    print(f"  {{*a, *b}} (a set)  : {sorted({*a, *b})}")
    print("  before 3.5 this was a + b, or list(a)+list(b) for mixed iterables.")
    print("  now the * splices any iterable straight into a new literal, mixed")
    print("  freely with individual elements - one expression, a NEW collection")

    print("--- ** inside a dict literal merges mappings ---")
    defaults = {"color": "black", "size": "M"}
    overrides = {"size": "L", "tag": "new"}
    combined = {**defaults, **overrides}
    print(f"  {{**defaults, **overrides}} : {combined}")
    print("  later keys WIN: size='L' from overrides beat size='M'. this is the")
    print("  merge that used to be d=dict(defaults); d.update(overrides) - now a")
    print("  single expression that builds a new dict without mutating either")

    print("--- ** with extra literal keys, in one expression ---")
    enriched = {**defaults, "shipping": "express", **overrides}
    print(f"  {{**defaults, 'shipping': 'express', **overrides}} : {enriched}")
    print("  you can interleave unpacked mappings and explicit key:value pairs,")
    print("  applied left to right, so building a config from a base plus")
    print("  additions plus overrides is one readable literal")

    print("--- * and ** in a function CALL, from multiple sources ---")
    def connect(host, port, *, timeout, retries):
        return f"{host}:{port} timeout={timeout} retries={retries}"
    address = ["db.local", 5432]
    options = {"timeout": 30, "retries": 3}
    print(f"  connect(*address, **options) : {connect(*address, **options)}")
    print("  *address supplies the positional args, **options the keyword args,")
    print("  from two separate objects - no temporary, no manual spreading. the")
    print("  call site assembles its arguments from wherever they live")

    print("--- multiple unpackings in ONE call (the part 3.5 newly allowed) ---")
    def total(*nums):
        return sum(nums)
    first = [1, 2]
    second = [3, 4]
    print(f"  total(*first, *second, 10) : {total(*first, *second, 10)}")
    print("  pre-3.5 a call could unpack only ONE iterable; 3.5 allowed several,")
    print("  mixed with literals. total(*first, *second, 10) sums 1+2+3+4+10")

    print("--- the idioms it replaced, side by side ---")
    print(f"  merge lists : a + b            -> [*a, *b]        = {[*a, *b]}")
    d_old = dict(defaults); d_old.update(overrides)
    print(f"  merge dicts : copy+update      -> {{**d1, **d2}}    = {combined}")
    print("  the old forms still work, but the unpacking literals say 'a NEW")
    print("  collection combining these' directly, without a mutation step or a")
    print("  helper - which is why they became the idiomatic way to merge")

    print("--- the constraint answered ---")
    print("  * and ** existed for assignment and single-call unpacking, but not")
    print("  inside literals or multi-source calls. PEP 448 (3.5) generalized")
    print("  them: [*a, *b], {**d1, **d2}, f(*a, *b, **kw). combining iterables")
    print("  or mappings into a new collection became a literal expression, not")
    print("  a copy-and-update procedure")


if __name__ == "__main__":
    main()
