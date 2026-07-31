"""Listing 196.1 - compiled code meets the matrix: suffixes, slots, and abi3.

Chapter 110 decoded the tags; this chapter compiles against them. The listing
builds REAL C extensions with the system compiler against each interpreter's
own headers, and lets the matrix demonstrate the whole compiled-wheel story:

  EXT_SUFFIX names the ABI at module level (.cpython-313 / -314 / -314t);
  an extension that does not declare free-threading support RE-ENABLES THE
  GIL when imported on 3.14t (Chapter 93's edge, caught in the act);
  one that declares Py_MOD_GIL_NOT_USED loads with the GIL still off;
  and the limited API (abi3) compiles on the GIL builds and REFUSES on the
  free-threaded build - Chapter 110's REJECT row, enforced by the headers.

Requires a C compiler (cc); compiles two twelve-line modules per run.
"""

import subprocess
import sys
import sysconfig
import tempfile
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch191.l01_the_tag_system import this_interpreter_tag  # noqa: E402

PLAIN_SRC = r'''
#define PY_SSIZE_T_CLEAN
#include <Python.h>
static PyObject *answer(PyObject *self, PyObject *args)
{ return PyLong_FromLong(42); }
static PyMethodDef methods[] =
{ {"answer", answer, METH_NOARGS, NULL}, {NULL, NULL, 0, NULL} };
static struct PyModuleDef mod =
{ PyModuleDef_HEAD_INIT, "MODNAME", NULL, -1, methods };
PyMODINIT_FUNC PyInit_MODNAME(void) { return PyModule_Create(&mod); }
'''

DECLARED_SRC = r'''
#define PY_SSIZE_T_CLEAN
#include <Python.h>
static PyObject *answer(PyObject *self, PyObject *args)
{ return PyLong_FromLong(43); }
static PyMethodDef methods[] =
{ {"answer", answer, METH_NOARGS, NULL}, {NULL, NULL, 0, NULL} };
static PyModuleDef_Slot slots[] = {
#ifdef Py_mod_gil
    {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
    {0, NULL}
};
static struct PyModuleDef mod =
{ PyModuleDef_HEAD_INIT, "MODNAME", NULL, 0, methods, slots };
PyMODINIT_FUNC PyInit_MODNAME(void) { return PyModuleDef_Init(&mod); }
'''


def compile_module(directory: Path, name: str, source: str,
                   limited: bool = False):
    src = directory / f"{name}.c"
    text = source.replace("MODNAME", name)
    if limited:
        text = "#define Py_LIMITED_API 0x030B0000\n" + text
    src.write_text(text)
    suffix = ".abi3.so" if limited else sysconfig.get_config_var("EXT_SUFFIX")
    out = directory / f"{name}{suffix}"
    result = subprocess.run(
        ["cc", "-shared", "-undefined", "dynamic_lookup",
         f"-I{sysconfig.get_path('include')}", str(src), "-o", str(out)],
        capture_output=True, text=True)
    return result.returncode == 0


def gil_enabled():
    return sys._is_gil_enabled()


def main() -> None:
    print("--- the ABI in the filename, at module level ---")
    print(f"  EXT_SUFFIX : {sysconfig.get_config_var('EXT_SUFFIX')}")
    print("  the suffix is the wheel tag's abi field applied per FILE, so one")
    print("  directory can hold builds for several interpreters side by side")

    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        sys.path.insert(0, str(build))
        try:
            print("--- a well-behaved citizen: declares its GIL position ---")
            ok = compile_module(build, "declared", DECLARED_SRC)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                import declared
            print(f"  compiled and imported : {ok}, answer() = "
                  f"{declared.answer()}")
            print(f"  import warned          : {bool(caught)}")
            print(f"  GIL enabled afterwards : {gil_enabled()}")
            print("  Py_mod_gil = Py_MOD_GIL_NOT_USED (multi-phase init): on the")
            print("  free-threaded build this module loads WITHOUT re-arming the")
            print("  GIL; on GIL builds the slot is an inert declaration")

            print("--- a legacy module: no declaration ---")
            ok = compile_module(build, "legacy", PLAIN_SRC)
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                import legacy
            print(f"  compiled and imported : {ok}, answer() = "
                  f"{legacy.answer()}")
            print(f"  import warned          : {bool(caught)}")
            print(f"  GIL enabled afterwards : {gil_enabled()}")
            print("  on 3.14t this import RE-ENABLES the GIL for the whole")
            print("  process (with a RuntimeWarning): one undeclared wheel and")
            print("  Chapter 93's scaling is gone - which is why cp314t wheels")
            print("  are a separate, opt-in universe (Chapter 110)")

            print("--- the limited API, tried against these headers ---")
            ok = compile_module(build, "stable", PLAIN_SRC, limited=True)
            print(f"  Py_LIMITED_API compile succeeded : {ok}")
            print("  the GIL builds accept it and emit an .abi3.so usable on")
            print("  every CPython >= 3.11; the free-threaded headers REFUSE it")
            print("  outright - Chapter 110's REJECT row, enforced at compile")
            print("  time rather than install time")

            print("--- what this module's wheel would be named ---")
            arch = sysconfig.get_platform().rsplit("-", 1)[-1]
            tag = this_interpreter_tag()
            print(f"  cmod-1.0-{tag}-{tag}-macosx_<floor>_{arch}.whl")
            print("  one such wheel per interpreter ABI per platform: the build")
            print("  matrix that cibuildwheel-style tooling exists to generate,")
            print("  and that abi3 exists to collapse (where it is allowed)")
        finally:
            sys.path.remove(str(build))
            sys.modules.pop("declared", None)
            sys.modules.pop("legacy", None)


if __name__ == "__main__":
    main()
