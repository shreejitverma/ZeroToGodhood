"""Helper module for Listing 63.1. Its body runs once per interpreter (on first
import), and records that fact in a builtins counter so the caller can see how
many times the body actually executed across repeated imports."""
import builtins

# This line runs only when the module body executes (first import, or a reload).
builtins._importonce_loads = getattr(builtins, "_importonce_loads", 0) + 1

# Simulate nontrivial import-time work (compiling a table, loading data, ...).
SQUARES = [i * i for i in range(1000)]
TOTAL = sum(SQUARES)
