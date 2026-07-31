"""Listing 250.1 - Python 3.3 (2012): unittest.mock, test doubles in the standard library.

Testing code that talks to the outside world - a payment gateway, a clock, a
database - means you cannot call the real thing in a unit test. You need a stand-in
that records how it was called and returns what you tell it. People hand-wrote
these 'test doubles' as ad-hoc fake classes, differently every time. The popular
third-party `mock` library solved it well, and Python 3.3 pulled it into the
standard library as unittest.mock. A Mock records every call and lets you script
its return value; patch() temporarily replaces a real object with a mock for the
duration of a test. Deep volumes own no test mechanism; this is the release that
made test doubles a batteries-included tool. Verified on current interpreters.
"""

from unittest.mock import Mock, MagicMock, patch


# A module-level function we will later replace with a mock via patch().
def send_email(to, subject):
    raise RuntimeError("real send_email must never run in a test")


def notify(user, mailer):
    """Business logic that depends on a collaborator (mailer)."""
    return mailer.send(user["email"], "Welcome")


def main() -> None:
    print("--- a Mock records how it was called ---")
    mailer = Mock()
    mailer.send.return_value = "queued"          # script the return value
    result = notify({"email": "ada@x.io"}, mailer)
    print(f"  notify(...) returned : {result}")
    print(f"  mailer.send.called      : {mailer.send.called}")
    print(f"  mailer.send.call_count  : {mailer.send.call_count}")
    print(f"  called with args        : {mailer.send.call_args}")
    print("  the Mock stood in for a real mailer: it recorded the call and")
    print("  returned the scripted 'queued'. no real email, full record of how")
    print("  the code under test used its collaborator")

    print("--- assert_called_with: state the expected interaction ---")
    mailer.send.assert_called_with("ada@x.io", "Welcome")
    print("  assert_called_with(...) passed (no exception): the code called")
    print("  send with exactly those arguments. this is how you test BEHAVIOUR")
    print("  - what the code did to its dependency - not just its return value")
    try:
        mailer.send.assert_called_with("wrong@x.io", "Welcome")
    except AssertionError:
        print("  asserting the WRONG args raised AssertionError, as it should")

    print("--- side_effect: make a mock raise, or return a sequence ---")
    flaky = Mock()
    flaky.side_effect = [1, 2, ValueError("boom")]  # per-call script
    print(f"  first call  : {flaky()}")
    print(f"  second call : {flaky()}")
    try:
        flaky()                                  # third: raises
    except ValueError as exc:
        print(f"  third call raises : ValueError({exc})")
    print("  side_effect scripts a SEQUENCE of returns (or exceptions), so you")
    print("  can simulate retries, transient failures, and exhausted resources")

    print("--- MagicMock supports dunder operations too ---")
    mm = MagicMock()
    mm.__len__.return_value = 3
    mm.__getitem__.return_value = "x"
    print(f"  len(magicmock) : {len(mm)}")
    print(f"  magicmock[0]   : {mm[0]}")
    print("  a plain Mock does not implement __len__/__getitem__; MagicMock does,")
    print("  so it can stand in for list-like or dict-like collaborators")

    print("--- patch(): replace a real object for the duration of a block ---")
    with patch(f"{__name__}.send_email") as fake_send:
        fake_send.return_value = "sent"
        out = send_email("ada@x.io", "Hi")       # the mock, not the real one
        print(f"  inside patch, send_email(...) : {out}")
        print(f"  fake_send.called : {fake_send.called}")
    print(f"  outside patch, send_email is the real function again : "
          f"{send_email.__name__ == 'send_email'}")
    print("  patch() swapped the real send_email for a mock inside the block and")
    print("  restored it after - so a test never touches the real service, and")
    print("  the replacement is automatically undone")

    print("--- the constraint answered ---")
    print("  testing code with external dependencies needed stand-ins that")
    print("  record calls and script returns - hand-written differently every")
    print("  time. unittest.mock (3.3) made them standard: Mock records and")
    print("  scripts, side_effect simulates failure, patch() swaps reals for")
    print("  fakes and restores them. test doubles became batteries-included")


if __name__ == "__main__":
    main()
