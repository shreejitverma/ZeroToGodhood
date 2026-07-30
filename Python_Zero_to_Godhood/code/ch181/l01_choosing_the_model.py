"""Listing 181.1 - choosing a concurrency model: the volume, as a decision.

Deep L closes the way Deep K and Deep M closed: with the decision procedure the
volume has been building. Four primitives, each measured in its own chapter;
one table of properties; one piece of amortisation arithmetic that turns the
measured boundary prices into minimum task sizes; and the procedure that picks
a primitive from the workload rather than from fashion.

Everything printed here is either a property established earlier in the volume
or arithmetic on a measured constant, with the chapter that owns it named.
"""


def main() -> None:
    print("--- the four primitives, as measured properties ---")
    rows = (
        ("threads (GIL build)", "none for CPU (Ch 93)", "queue hop", "full (Ch 99)", "none"),
        ("threads (3.14t)", "cores (3.7x, Ch 93)", "queue hop", "full (Ch 99)", "none"),
        ("subinterpreters", "cores (3.8x, Ch 98)", "marshal/copy", "none: isolated", "none"),
        ("processes", "cores (3.7x, Ch 98)", "pickle + IPC", "none: isolated", "full"),
    )
    print(f"  {'primitive':<20} {'CPU scaling':<21} {'boundary':<13} "
          f"{'race burden':<15} {'fault isolation'}")
    for name, scale, boundary, burden, fault in rows:
        print(f"  {name:<20} {scale:<21} {boundary:<13} {burden:<15} {fault}")
    print("  asyncio is deliberately absent: it interleaves WAITING, not")
    print("  computing (Deep H), and composes with any row for the I/O half")

    print("--- amortisation: boundary price to minimum task size ---")
    print("  rule: for >= 95% efficiency, task work must exceed ~20x the")
    print("  per-task boundary price (measured per grain in bench 181.1)")
    prices = (
        ("thread hand-off", 1, "Ch 98: queue round trip, sub-us"),
        ("interpreter crossing", 7, "Ch 98/181: ~7 us per task, GIL build"),
        ("process crossing", 47, "Ch 181: ~47 us per task"),
    )
    for label, us, source in prices:
        print(f"  {label:<22} ~{us:>3} us  -> tasks of >= {us * 20 / 1000:5.2f} ms"
              f"   ({source})")
    print("  below the line, batch: Chapter 84's rule at architecture scale.")
    print("  fine-grained work survives only the cheapest boundary, which is")
    print("  why grain is a DESIGN INPUT, not an implementation detail")

    print("--- the decision procedure ---")
    steps = (
        ("waiting, not computing? asyncio or threads", "Deep H, Deep E"),
        ("CPU-bound and partitionable? partition-and-merge on the", ""),
        ("  cheapest scaling primitive: 3.14t threads, else", "Ch 93, 99"),
        ("  subinterpreters (in-process) or processes", "Ch 98"),
        ("must share mutable state? free-threaded threads,", ""),
        ("  under Chapter 99's discipline, sized by Ch 94-97's costs", "Ch 94-99"),
        ("need fault isolation or memory caps? processes", "Ch 98"),
        ("then set the grain: task >> boundary price, batched", "Ch 84, 181"),
    )
    for i, (step, where) in enumerate(steps, 1):
        suffix = f"  ({where})" if where else ""
        print(f"  {step:<58}{suffix}")

    print("--- Deep L, closed ---")
    print("  93  two escapes: shared-everything and shared-nothing, measured")
    print("  94  the refcount, split: ownership is the new cost axis")
    print("  95  memory: the allocator scales, the collector stops the world")
    print("  96  container locks: private scales, shared mutation collapses")
    print("  97  thread-local bytecode: the specializer without its assumption")
    print("  98  subinterpreters: isolation as the primitive")
    print("  99  correctness: test where the races are visible")
    print("  100 this chapter: the workload picks the primitive")
    print("  the GIL was one price for everything; its replacements are a price")
    print("  LIST, and the engineering is reading it before the design is set")


if __name__ == "__main__":
    main()
