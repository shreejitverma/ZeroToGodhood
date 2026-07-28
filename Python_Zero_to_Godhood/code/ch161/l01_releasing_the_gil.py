"""Listing 161.1 - who releases the GIL at the C boundary, and how you can tell.

A C function called from Python does not touch Python objects, so nothing it does
requires the GIL. If the caller RELEASES the GIL for the duration of the call, other
Python threads keep running and the process gets real parallelism out of that C work.
If the caller holds it, every other Python thread is stopped for the whole call.

ctypes makes the choice explicit in the loader you pick:

  ctypes.CDLL   - RELEASES the GIL around every call. The default, and the right one.
  ctypes.PyDLL  - HOLDS the GIL. Required only when the C function itself calls into
                  the CPython C-API, which is why the C-API functions live behind
                  ctypes.pythonapi, a PyDLL.

and in the callback factory:

  ctypes.CFUNCTYPE   - the callback ACQUIRES the GIL on entry (it is entered from C).
  ctypes.PYFUNCTYPE  - the callback assumes the GIL is already held.

This listing proves the difference by observation rather than by citation: a worker
thread spends 300 ms inside a C sleep while the main thread tries to run Python. Under
CDLL the main thread runs concurrently and the whole sequence takes about 100 ms. Under
PyDLL the main thread cannot execute a single bytecode until the C call returns, so the
same sequence takes about 400 ms. The margin is four-fold, so the reported booleans are
stable; the wall-clock numbers themselves are the benchmark's job.
"""

import ctypes
import ctypes.util
import threading
import time

C_SLEEP_US = 300_000        # 300 ms spent inside C
SETTLE_S = 0.05             # let the worker actually enter the C call
OBSERVE_S = 0.05            # how long the main thread tries to run Python
OVERLAP_LIMIT_S = 0.20      # midpoint between the ~0.10 s and ~0.40 s outcomes


def ran_during_c_call(loader):
    """Start a thread that sleeps in C; report whether the main thread kept running."""
    lib = loader(ctypes.util.find_library("c"))
    lib.usleep.argtypes = [ctypes.c_uint]
    lib.usleep.restype = ctypes.c_int

    started = threading.Event()

    def worker():
        started.set()
        lib.usleep(C_SLEEP_US)

    thread = threading.Thread(target=worker)
    begin = time.perf_counter()
    thread.start()
    started.wait()
    time.sleep(SETTLE_S)

    spins = 0
    deadline = time.perf_counter() + OBSERVE_S
    while time.perf_counter() < deadline:
        spins += 1
    elapsed = time.perf_counter() - begin
    thread.join()
    return elapsed < OVERLAP_LIMIT_S, spins > 0


def main() -> None:
    # The choice is one bit in the function flags: _FUNCFLAG_PYTHONAPI (0x4) means
    # "this call touches the CPython C-API, so do not release the GIL".
    hold = ctypes._FUNCFLAG_PYTHONAPI

    print("--- the choice is one flag bit, not a convention ---")
    print(f"  _FUNCFLAG_PYTHONAPI (hold the GIL)  : {hold}")
    for name, flags in (("CDLL", ctypes.CDLL._func_flags_),
                        ("PyDLL", ctypes.PyDLL._func_flags_)):
        verb = "holds the GIL for the call" if flags & hold else "releases it for the call"
        print(f"  {name:<11} flags={flags}  ->  {verb}")
    for name, flags in (("CFUNCTYPE", ctypes.CFUNCTYPE(None)._flags_),
                        ("PYFUNCTYPE", ctypes.PYFUNCTYPE(None)._flags_)):
        verb = "assumes the GIL is held" if flags & hold else "acquires the GIL on entry"
        print(f"  {name:<11} flags={flags}  ->  {verb}")
    print(f"  ctypes.pythonapi is a PyDLL         : "
          f"{isinstance(ctypes.pythonapi, ctypes.PyDLL)}")

    print("--- observation: does another thread run while C runs? ---")
    cdll_overlapped, cdll_spun = ran_during_c_call(ctypes.CDLL)
    pydll_overlapped, pydll_spun = ran_during_c_call(ctypes.PyDLL)
    print(f"  CDLL  : main thread ran during the C call : {cdll_overlapped}")
    print(f"  PyDLL : main thread ran during the C call : {pydll_overlapped}")
    print(f"  both eventually executed Python           : {cdll_spun and pydll_spun}")

    print("--- the same rule inside the standard library ---")
    print("  hashlib, zlib, and the io and socket layers release the GIL around their")
    print("  C work, which is why hashing four buffers in four threads scales and")
    print("  hashing them in four Python loops does not")

    print("--- the rule ---")
    print("  release the GIL for any C call that does not touch Python objects; hold it")
    print("  only when the C code calls the CPython C-API, and pay for it in parallelism")


if __name__ == "__main__":
    main()
