"""Listing 89.1 - TypedDict: static types over dict-shaped data at zero runtime cost.

Data often arrives as dicts, a JSON body, a database row, **kwargs, a config. You
want static key/type checking without converting it to a class. A TypedDict does
exactly that: it declares the keys and value types for the checker, while at
RUNTIME it IS a plain dict (no new type, no conversion, no per-record object). A
dataclass gives a real typed object with attribute access and behavior, but you
must CONVERT each dict into an instance, which costs (the benchmark measures 6.3x).
So TypedDict types data that is already dicts in place; a dataclass is for domain
objects worth building. This listing shows the runtime identity.
"""

from dataclasses import dataclass
from typing import TypedDict


class UserTD(TypedDict):
    id: int
    name: str


@dataclass
class UserDC:
    id: int
    name: str


def main() -> None:
    print("--- a TypedDict is a plain dict at runtime ---")
    u = UserTD(id=1, name="Ada")
    print(f"  type(UserTD(...))     : {type(u).__name__}")
    print(f"  isinstance(u, dict)   : {isinstance(u, dict)}")
    print(f"  access by key         : {u['id']}, {u['name']}")
    print(f"  equals a plain dict   : {u == {'id': 1, 'name': 'Ada'}}")

    print("--- so JSON data needs NO conversion to be typed ---")
    from_json = {"id": 2, "name": "Bjarne"}     # e.g. json.loads(...)
    typed: UserTD = from_json                     # the checker treats it as UserTD; runtime: same dict
    print(f"  used in place, still a dict : {typed is from_json}")
    print(f"  no new object allocated     : {type(typed).__name__ == 'dict'}")

    print("--- a dataclass is a real object: attribute access, but a conversion ---")
    d = UserDC(**from_json)                       # build an instance from the dict
    print(f"  type(UserDC(...))     : {type(d).__name__}")
    print(f"  attribute access      : {d.id}, {d.name}")
    print(f"  a new object per dict : {type(d).__name__ != 'dict'}")

    print("--- the rule ---")
    print(f"  TypedDict: type dict-shaped data (JSON/kwargs/config) IN PLACE, free")
    print(f"  dataclass: a real typed object (attributes, methods, validation), at a")
    print(f"             per-record conversion cost")


if __name__ == "__main__":
    main()
