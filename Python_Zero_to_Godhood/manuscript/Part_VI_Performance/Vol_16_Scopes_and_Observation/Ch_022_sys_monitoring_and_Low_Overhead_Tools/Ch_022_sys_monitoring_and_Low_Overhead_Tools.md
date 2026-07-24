# Chapter 22: `sys.monitoring` and Low-Overhead Tools (Python 3.12)

Turn on line coverage for a test suite built with an older coverage tool and watch it run three times
slower. The reason is not the coverage bookkeeping itself; it is the mechanism the tool had to use.
Until Python 3.12, a debugger, profiler, or coverage tool observed execution through `sys.settrace`,
which installs *one global tracer* that the interpreter calls on every line of every frame in the
program. That per-line call is expensive on its own, and it does something worse: a traced frame cannot
run the specialized opcodes of Chapter 17, so tracing does not merely add overhead, it *turns off* the
fast interpreter for everything it touches.

Python 3.12 replaced that model. **PEP 669** added `sys.monitoring`: a tool subscribes to specific
*events* under a tool id, and the interpreter invokes its callback only when one of those events
actually fires, on only the code objects the tool asked to watch. Idle monitoring costs nothing, and
the measurement in this chapter shows why the entire tooling ecosystem moved to it. This chapter sits
alongside PEP 695 (Chapter 18) in the 3.12 story: both are about the interpreter becoming more
observable and more controllable without giving up the speed the 3.11 work bought.

## Section index

- **22.1** The problem: monitoring that taxes everything
- **22.2** `sys.monitoring`: events, tools, and callbacks
- **22.3** Measurement: `settrace` versus `sys.monitoring`
- **22.4** Edges and failure modes
- **22.5** Connections
- **22.6** Exercises
- **22.7** Summary and cross-references

Listings live under `code/ch022/` and are re-executed by `make verify` on both interpreters.

---

## 22.1 The problem: monitoring that taxes everything

`sys.settrace` is a single, global, per-frame hook. When it is installed, the interpreter calls the
trace function on frame entry and, if the function asks, on every line and every exception in that
frame, for *all* code, whether or not the tool cares about it. A coverage tool that only needs to know
which lines executed pays the per-line dispatch on every line of every module, and a debugger that only
cares about one function pays it everywhere.

The deeper cost is the interaction with the specializing interpreter (Chapter 17). Specialized opcodes
assume the normal execution path; a frame under `settrace` runs an instrumented path that cannot use
them, so tracing silently reverts hot, specialized code to the generic interpreter. The tool's overhead
is therefore not a fixed per-line cost but a *loss of the 3.11 speedups* on everything it observes.
That is the tax `sys.monitoring` was designed to remove.

---

## 22.2 `sys.monitoring`: events, tools, and callbacks

The `sys.monitoring` model has three pieces: *events* (the things that can be observed, `CALL`, `LINE`,
`RETURN`, `BRANCH`, `RAISE`, and more), *tool ids* (a small set of namespaced slots so a debugger, a
coverage tool, and a profiler can monitor at once without colliding), and *callbacks* (the function the
interpreter calls when a subscribed event fires).

```python
# code/ch022/l01_monitoring.py
mon = sys.monitoring
TOOL = mon.PROFILER_ID
mon.use_tool_id(TOOL, "call-recorder")

def on_call(code, instruction_offset, callable_obj, arg0):
    name = getattr(callable_obj, "__name__", None)
    if name in ("foo", "bar"):
        observed.append(name)

mon.register_callback(TOOL, mon.events.CALL, on_call)
mon.set_events(TOOL, mon.events.CALL)
```

Verified output (CPython 3.13.5):

```text
--- the event set a tool can subscribe to ---
  events include: BRANCH, CALL, C_RAISE, C_RETURN, EXCEPTION_HANDLED, INSTRUCTION, JUMP, LINE ...
--- the CALL callback observed the calls, with zero source changes ---
  observed calls: ['foo', 'bar']
```

The callback recorded both function calls with no change to `foo` or `bar`. Two properties make this
different from `settrace`. First, the tool subscribes to *one* event (`CALL`), so the interpreter does
not pay for `LINE` or `BRANCH` it did not ask for. Second, `set_events(TOOL, 0)` disables monitoring
and the interpreter returns the code to full specialized speed; monitoring is a state you enter and
leave, not a global mode that colors everything while any tool is active. (The event set itself drifted
slightly in 3.14, which added `BRANCH_LEFT`/`BRANCH_RIGHT`; the core events and the API are stable, and
both interpreters are recorded.)

---

## 22.3 Measurement: `settrace` versus `sys.monitoring`

The chapter opened with a 3x coverage slowdown. Here it is measured directly.

**Methodology.** `code/ch022/bench_monitoring_overhead.py`. A one-million-iteration integer loop run
three ways: with no tools, under a `sys.settrace` line tracer, and under a `sys.monitoring` tool
registered with *no events enabled* (the idle case). `min` of five runs. CPython 3.13.5, Apple M3 Pro,
macOS 27.0, arm64.

| observation mode | ratio |
|---|---|
| no tools (baseline) | 1.00x |
| `sys.settrace` line tracer | **2.67x** |
| `sys.monitoring`, no events enabled | **0.95x** |

**A global `settrace` line tracer costs 2.67x** on this tight loop, because it fires per line and forces
the frame off the specialized path. A `sys.monitoring` tool registered with no events enabled costs
**nothing** (0.95x is noise), because the interpreter runs at full speed until a subscribed event
actually fires. That is the whole design difference: `settrace` is pay-when-installed and taxes
everything; `sys.monitoring` is pay-per-event and taxes only what a tool watches. A modern coverage
tool subscribes to `LINE` for only the code objects under test and leaves the rest of the interpreter
running at 3.11 speed, which is why the ecosystem, coverage.py, debuggers, sampling profilers, moved to
it. The full profiling-methodology treatment, including `perf`, `py-spy`, and `tracemalloc`, is **Deep
K**.

---

## 22.4 Edges and failure modes

**Reaching for `settrace` in new tooling.** §22.3. It is 2.67x here and defeats specialization. New
debuggers, coverage tools, and profilers should use `sys.monitoring`.

**Enabling more events than you need.** `sys.monitoring` is cheap because it is selective; subscribing
to `LINE` or `INSTRUCTION` globally reintroduces much of the `settrace` cost. Enable the narrowest event
and the smallest set of code objects that answers your question.

**Tool-id collisions.** The tool-id slots are finite and namespaced. Always `use_tool_id` before and
`free_tool_id` after; leaking a tool id can block another tool. Wrap acquisition and release so an
exception does not leave monitoring on.

**Leaving monitoring on.** Forgetting `set_events(TOOL, 0)` leaves the subscribed code paths
instrumented, silently slowing them. Disable when done.

**Assuming the event set is stable.** §22.2. 3.14 added `BRANCH_LEFT`/`BRANCH_RIGHT`. Query
`sys.monitoring.events` rather than hard-coding the list.

---

## 22.5 Connections

**Backward.** The specializing interpreter that `settrace` defeats and `sys.monitoring` coexists with is
Chapter 17. The frame and code-object model the events fire against is Chapter 2. The exception events
(`RAISE`, `EXCEPTION_HANDLED`) observe the exception table of Chapter 6.

**Forward.** Profiling methodology in full, sampling versus deterministic profilers, `perf`, `py-spy`,
`tracemalloc`, and how to not lie with a benchmark, is **Deep K**, which builds its tooling on this API.
The debugger built on `sys.monitoring` is part of the testing-and-debugging treatment in **Deep O**.

**Across books.** Low-overhead monitoring is how a Book II service stays observable in production without
the tracing tax. A retrieval service in **Book III** can run a sampling profiler built on
`sys.monitoring` in production to find hot code, where a `settrace`-based profiler would have been too
expensive to leave on. The same applies to a latency-sensitive path calling into **Book I**: you can
observe it without slowing it. **Deep K** owns the methodology; this chapter is the interpreter feature
it rests on.

---

## 22.6 Exercises

**1. Watch a specific event.** Register a `sys.monitoring` tool for the `LINE` event and record which
lines of a small function execute. Then add the `RETURN` event and record the return values. Explain how
this differs from `settrace` in what the interpreter pays.

**2. Measure your own coverage tax.** Reproduce §22.3's benchmark, then write a minimal line-coverage
recorder with `sys.monitoring` (subscribe to `LINE`, record `(code, line)` pairs) and measure *its*
overhead against the `settrace` version. Report to the standard of §22.3.

**3. Prove specialization returns.** Warm a monomorphic function so it specializes (Chapter 17), enable
`sys.monitoring` on it, disable it, and confirm with `dis(..., adaptive=True)` whether the specialized
opcodes survive. Explain what you find.

**4. Namespace two tools.** Register a debugger tool and a profiler tool with different ids
simultaneously, each watching a different event, and show they do not interfere. Explain why the tool-id
namespacing is necessary.

**5. The design question.** PEP 669 chose an event-subscription model with a fixed small number of tool
ids, rather than an arbitrary callback registry. Argue why. Your answer must address the per-event cost,
why coexistence with the specializing interpreter required a new API rather than optimizing `settrace`,
and what the fixed tool-id count buys.

---

## 22.7 Summary and cross-references

- Before 3.12, tools observed execution through **`sys.settrace`**, one global per-frame tracer that
  fires on every line and **defeats the specializing interpreter**, so tracing loses the 3.11 speedups
  on everything it touches.
- **`sys.monitoring`** (PEP 669) is event-based: a tool subscribes to specific **events** under a **tool
  id** and the interpreter calls its **callback** only when a subscribed event fires, on only the
  watched code objects.
- **Measured:** a `settrace` line tracer costs **2.67x**; a `sys.monitoring` tool with no events enabled
  costs **nothing** (0.95x). This is why coverage tools, debuggers, and profilers moved to it.
- Idle monitoring is free; the cost is proportional to the events and code you actually watch.

**Cross-references.** The specializing interpreter → Chapter 17. Frames and code objects → Chapter 2. The
exception table behind exception events → Chapter 6. Profiling methodology in full → Deep K. Debuggers
and testing → Deep O. The production-observability seams → Deep K.
