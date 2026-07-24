"""Listing 9.4 - one namespace package spanning two directories, with no
__init__.py anywhere.

Through 3.2 a directory was a package only if it contained __init__.py, which
blocked distributing one logical package (company.core, company.plugins) across
separate installs. PEP 420 lets a package span directories with no __init__.py:
PathFinder accumulates ALL matching directories into a namespace package whose
__path__ is the list of them and whose __file__ is None.

Self-contained: builds a two-directory layout in a temp dir, puts both on
sys.path, and imports one 'company' namespace from both.
"""

import os
import sys
import tempfile

root = tempfile.mkdtemp()

# path1/company/core/__init__.py  and  path2/company/extra/__init__.py
# with NO company/__init__.py in either path.
for path, sub, value in [("path1", "core", "from path1"), ("path2", "extra", "from path2")]:
    d = os.path.join(root, path, "company", sub)
    os.makedirs(d)
    with open(os.path.join(d, "__init__.py"), "w") as fh:
        fh.write(f"VALUE = {value!r}\n")

sys.path.insert(0, os.path.join(root, "path1"))
sys.path.insert(0, os.path.join(root, "path2"))

import company             # no __init__.py anywhere -> namespace package
import company.core        # contributed by path1
import company.extra       # contributed by path2

print("--- one importable 'company' namespace, two contributing directories ---")
print("  company.__file__      :", company.__file__)
print("  number of __path__ entries:", len(list(company.__path__)))
print("  company.core.VALUE    :", company.core.VALUE)
print("  company.extra.VALUE   :", company.extra.VALUE)
print()
print("__file__ is None and __path__ has multiple entries: the signature of a")
print("namespace package. This is how zope.*, google.cloud.*, and internal")
print("company.* namespaces ship as independent, separately-installable")
print("distributions. The footgun: dropping an __init__.py from a REGULAR")
print("package silently turns it into a namespace package.")
