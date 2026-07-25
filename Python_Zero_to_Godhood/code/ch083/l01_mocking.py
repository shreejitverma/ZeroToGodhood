"""Listing 83.1 - mock where a name is USED, and autospec to catch signature bugs.

Two mocking pitfalls. (1) Patch target: `from mod import func` binds func into the
IMPORTING module's namespace, so patching mod.func does nothing to code that
already holds its own reference, you must patch the name where it is LOOKED UP
(the using module), not where it is defined. (2) A bare Mock accepts ANY call
(any args, any attribute), so if the real function's signature changes, the test
keeps passing against a mock that no longer matches, a false green. create_autospec
builds a mock constrained to the real object's signature, so a wrong call fails
the test. This listing shows both.

svc/clock.py defines now(); svc/app.py does `from ...clock import now`.
"""

import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ch083.svc import app  # noqa: E402


def main() -> None:
    print("--- patch where DEFINED (clock.now): no effect on app ---")
    with mock.patch("ch083.svc.clock.now", return_value="FAKE"):
        print(f"  app.timestamp() : {app.timestamp()!r}  (still real: app has its own 'now')")

    print("--- patch where USED (app.now): works ---")
    with mock.patch("ch083.svc.app.now", return_value="FAKE"):
        print(f"  app.timestamp() : {app.timestamp()!r}  (mocked)")

    print("--- a bare Mock accepts ANY call (hides signature bugs) ---")
    m = mock.Mock()
    m(1, 2, 3, key="anything")          # no error, whatever the real signature is
    print(f"  bare Mock accepted 4 args : {m.called}")

    print("--- autospec constrains the mock to the real signature ---")
    # app.timestamp() takes NO arguments
    spec = mock.create_autospec(app.timestamp)
    spec()                              # correct: no args -> ok
    print(f"  autospec accepted 0 args  : {spec.called}")
    try:
        spec(1, 2, 3)                   # wrong: real timestamp takes no args
        rejected = False
    except TypeError:
        rejected = True
    print(f"  autospec rejected 3 args  : {rejected}  (a bare Mock would not)")


if __name__ == "__main__":
    main()
