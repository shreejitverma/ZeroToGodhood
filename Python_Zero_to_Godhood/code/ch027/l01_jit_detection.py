"""Listing 27.1 - detecting the JIT, which is a build-time option and off here.

PEP 744 (3.13) added an experimental copy-and-patch JIT, built only when CPython
is configured with --enable-experimental-jit. 3.14 exposes sys._jit to query it.
On a default build (like this book's) the JIT is not compiled in, so is_available
is False. This listing shows the detection API; the performance discussion is
cited, not measured, because no JIT-enabled build is in the verification matrix.
"""

import sys
import sysconfig

print("--- is the JIT available and enabled on this interpreter? ---")
if hasattr(sys, "_jit"):
    print("  sys._jit.is_available():", sys._jit.is_available())
    print("  sys._jit.is_enabled()  :", sys._jit.is_enabled())
else:
    print("  sys._jit: not present on this version")

ca = sysconfig.get_config_var("CONFIG_ARGS") or ""
print("  built with --enable-experimental-jit:", "experimental-jit" in ca)
print()
print("This is a default build: the JIT was not compiled in, so is_available is")
print("False. A JIT-enabled build (configured with --enable-experimental-jit,")
print("and toggled at runtime with PYTHON_JIT=1) would report True. The JIT")
print("consumes the SAME specialized micro-ops the specializing interpreter")
print("produces (Chapter 17); it does not replace specialization, it builds on it.")
