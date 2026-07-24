"""Listing 10.2 - paths as objects: the / join operator and pure-vs-concrete
paths.

Before 3.4 a path was a str manipulated with a grab-bag of os.path functions.
pathlib (PEP 428) makes a path a typed object with an overloaded / join
operator, rich component accessors, and a clean split between pure paths (string
algebra, no I/O, can parse foreign paths) and concrete paths (filesystem I/O).
Path(".") instantiates PosixPath or WindowsPath for the host OS.
"""

from pathlib import Path, PureWindowsPath

p = Path("/var") / "log" / "nginx.log"     # __truediv__ joins, per-OS separators

print("--- component algebra with no syscalls ---")
print("  joined     :", p)
print("  parts      :", p.parts)
print("  name       :", p.name)
print("  suffix     :", p.suffix)
print("  stem       :", p.stem)
print("  with_suffix:", p.with_suffix(".gz"))
print("  parent     :", p.parent)

print()
print("--- a pure path can parse a foreign OS's paths on this host ---")
print("  PureWindowsPath('C:/a/b'):", PureWindowsPath("C:/a/b"))
print("  Path('.') concrete type  :", type(Path(".")).__name__)

print()
print("The / operator reads naturally and handles separators per-OS, so the")
print("same code is correct on Windows and POSIX. Path unifies read_text,")
print("write_bytes, glob, mkdir, exists, stat; prefer it over os.path in new")
print("code. The stdlib now accepts path-like objects everywhere via os.PathLike.")
