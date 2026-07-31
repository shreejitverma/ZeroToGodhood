"""Canonical book structure for Python: Zero to Godhood.

The manuscript directory tree is inconsistent (volumes are filed under the wrong
part directories), so the authoritative reading order comes from CANONICAL_TOC.md,
transcribed here as an explicit ordered list. Each volume is anchored by its label
(Vol_NN or Deep_X), which maps to exactly one directory anywhere under manuscript/.
"""

# (part_number, part_title, part_subtitle, [ (volume_label, volume_kind, volume_title) ... ])
# volume_kind: "timeline" or "deep"
PARTS = [
    ("I", "Origins", "1989 - 1995", [
        ("Vol_01", "timeline", "Before Python"),
        ("Vol_02", "timeline", "The 1.x Language"),
        ("Deep_A", "deep", "The Object Model"),
        ("Deep_B", "deep", "Memory: Allocator and GC"),
    ]),
    ("II", "The 2.x Ascent", "1995 - 2010", [
        ("Vol_03", "timeline", "The Licence Rupture and 2.0"),
        ("Vol_04", "timeline", "Unification"),
        ("Deep_C", "deep", "Types, Descriptors, Metaclasses"),
        ("Vol_05", "timeline", "Syntax for Control"),
        ("Vol_06", "timeline", "The 2.7 Twilight"),
    ]),
    ("III", "The Break", "2008 - 2012", [
        ("Vol_07", "timeline", "The Schism"),
        ("Deep_D", "deep", "Text, Bytes, Encodings"),
        ("Vol_08", "timeline", "Consolidation"),
        ("Deep_E", "deep", "Concurrency I: GIL, Threads, Processes"),
    ]),
    ("IV", "Iteration and Async", "2012 - 2015", [
        ("Vol_09", "timeline", "Delegation"),
        ("Deep_F", "deep", "Iteration, Generators, Coroutines"),
        ("Deep_G", "deep", "The Import System"),
        ("Vol_10", "timeline", "Provisional"),
        ("Vol_11", "timeline", "Native Syntax"),
        ("Deep_H", "deep", "Concurrency II: asyncio and Structured Concurrency"),
    ]),
    ("V", "Ergonomics and Typing", "2016 - 2021", [
        ("Vol_12", "timeline", "Expression"),
        ("Deep_I", "deep", "The Type System"),
        ("Vol_13", "timeline", "Binding and Debt"),
        ("Vol_14", "timeline", "Structure"),
    ]),
    ("VI", "Performance", "2022 - 2023", [
        ("Vol_15", "timeline", "The Specializing Interpreter"),
        ("Vol_16", "timeline", "Scopes and Observation"),
        ("Deep_J", "deep", "The Interpreter: ceval, Bytecode, JIT"),
        ("Deep_K", "deep", "Performance Engineering"),
    ]),
    ("VII", "The Concurrency Reckoning", "2024 - ", [
        ("Vol_17", "timeline", "Free-Threading Arrives"),
        ("Vol_18", "timeline", "Deferred and Supported"),
        ("Deep_L", "deep", "Free-Threading and Subinterpreters"),
        ("Vol_19", "timeline", "The Frontier"),
    ]),
    ("VIII", "The Boundaries", "", [
        ("Deep_M", "deep", "The C-API, ABI, and FFI"),
        ("Deep_N", "deep", "Packaging and Distribution"),
        ("Deep_O", "deep", "Testing, Debugging, Observability, Security"),
    ]),
    ("IX", "The Standard Library", "", [
        ("Deep_P", "deep", "Text, Binary, Crypto"),
        ("Deep_Q", "deep", "Data, Time, Numerics, Functional"),
        ("Deep_R", "deep", "Persistence, OS, IPC, Networking"),
        ("Deep_S", "deep", "Runtime Services, Introspection, Tooling"),
    ]),
    ("X", "Applied Python", "", [
        ("Deep_T", "deep", "Numerical and Scientific"),
        ("Deep_U", "deep", "Data Engineering and Distributed"),
        ("Deep_V", "deep", "Web, Services, and the Trading Capstone"),
        ("Deep_W", "deep", "Quant Finance, ML, and Frontier Domains"),
    ]),
]
