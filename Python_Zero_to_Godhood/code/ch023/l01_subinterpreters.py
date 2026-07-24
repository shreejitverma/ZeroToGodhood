# requires: 3.14+
"""Listing 23.1 - a subinterpreter is an isolated Python inside one process, with
its own GIL.

PEP 684 (3.12) gave each subinterpreter its OWN Global Interpreter Lock, so N
subinterpreters can run N threads of Python bytecode truly in parallel, unlike N
threads in one interpreter (Chapter 8). PEP 734 (3.14) exposed the stdlib API,
concurrent.interpreters. Each subinterpreter has its own module state, its own
imports, and its own memory; they do not share objects, they pass data through
queues or channels.
"""

from concurrent import interpreters

# --- create an isolated interpreter and run code in it ---
interp = interpreters.create()
print("--- an isolated interpreter in the same process ---")
print("  created:", interp)

interp.exec("x = 40 + 2")
result = interp.call(lambda: 40 + 2)
print("  interp.call(lambda: 40 + 2):", result)

# --- state is isolated: the subinterpreter's x does not exist here ---
print("  'x' in this interpreter's globals:", "x" in globals())

# --- pass data through a Queue, since objects are not shared ---
q = interpreters.create_queue()
producer = interpreters.create()
producer.exec(f"""
from concurrent import interpreters
q = interpreters.Queue({q.id})
q.put("message from a subinterpreter")
""")
print("  queue.get():", q.get())

interp.close()
producer.close()
print()
print("Each subinterpreter is a separate Python: separate GIL, separate module")
print("state, separate memory. They share a process (so creation is far cheaper")
print("than a subprocess) but not objects (so there are no data races on shared")
print("state). Data crosses through queues, which copy or share only")
print("interpreter-safe values.")
