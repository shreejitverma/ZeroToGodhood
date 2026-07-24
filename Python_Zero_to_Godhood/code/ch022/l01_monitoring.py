"""Listing 22.1 - sys.monitoring observes execution without the global tax of
sys.settrace.

PEP 669 (3.12) added sys.monitoring: a tool registers a callback for specific
events (CALL, LINE, RETURN, BRANCH, ...) under a tool id, and the interpreter
invokes it only for those events. Unlike sys.settrace, which installs one global
per-frame tracer that fires on every line and defeats the specializing
interpreter, sys.monitoring is pay-for-what-you-enable and coexists with
specialization.
"""

import sys

mon = sys.monitoring

print("--- the event set a tool can subscribe to ---")
events = [e for e in dir(mon.events) if e.isupper() and not e.startswith("_")]
print("  events include:", ", ".join(sorted(events)[:8]), "...")

# Register a tool that records every function CALL.
TOOL = mon.PROFILER_ID
mon.use_tool_id(TOOL, "call-recorder")
observed = []


def on_call(code, instruction_offset, callable_obj, arg0):
    name = getattr(callable_obj, "__name__", None)
    if name in ("foo", "bar"):
        observed.append(name)


mon.register_callback(TOOL, mon.events.CALL, on_call)
mon.set_events(TOOL, mon.events.CALL)


def foo():
    return bar()


def bar():
    return 42


foo()

# Turn monitoring off and release the tool id.
mon.set_events(TOOL, 0)
mon.free_tool_id(TOOL)

print()
print("--- the CALL callback observed the calls, with zero source changes ---")
print("  observed calls:", observed)
print()
print("A tool id namespaces the monitoring: debuggers, coverage, and profilers")
print("each take an id (DEBUGGER_ID, COVERAGE_ID, PROFILER_ID) and do not")
print("interfere. set_events with 0 disables; the interpreter then runs the code")
print("at full specialized speed again.")
