# Verification and measurement entry points for Python Zero to Godhood, Book II.
#
# The book's central claim is that every "Verified output" block in the prose
# was produced by a program in this tree. `make verify` is what makes that
# claim checkable rather than aspirational.

PY313  ?= /opt/anaconda3/bin/python3
PY314  ?= python3
# The free-threaded build (PEP 703/779). A distinct verification target, keyed
# as `3.14t`; only the chapters that record output for it are checked on it.
PY314T ?= $(HOME)/.local/share/uv/python/cpython-3.14.6+freethreaded-macos-aarch64-none/bin/python3.14t
CH     ?=

.PHONY: help verify verify-313 verify-314 verify-314t crosscheck record record-314t bench interpreters clean

help:
	@echo "make verify        - listings on all interpreters, then prose cross-check"
	@echo "make crosscheck    - check output quoted in the prose matches the listings"
	@echo "make verify-313    - check on CPython 3.13 only"
	@echo "make verify-314    - check on CPython 3.14 only"
	@echo "make verify-314t   - check on the free-threaded 3.14 build (recorded chapters only)"
	@echo "make record        - regenerate expected output (review the diff before committing)"
	@echo "make record-314t   - record expected output on the free-threaded build (CH=chNNN)"
	@echo "make bench         - run benchmarks (results are never auto-committed)"
	@echo "make interpreters  - report the verification matrix and flag build mismatches"
	@echo ""
	@echo "Restrict to one chapter with CH=ch18, e.g. 'make verify CH=ch18'"

verify: verify-313 verify-314 verify-314t crosscheck

verify-313:
	@echo "=== CPython 3.13 ==="
	@$(PY313) -m _harness.verify $(CH)

verify-314:
	@echo "=== CPython 3.14 ==="
	@$(PY314) -m _harness.verify $(CH)

verify-314t:
	@echo "=== CPython 3.14 free-threaded ==="
	@if [ -x "$(PY314T)" ]; then \
		$(PY314T) -m _harness.verify --only-recorded $(CH); \
	else \
		echo "PY314T not found at $(PY314T); free-threaded leg NOT verified"; \
	fi

crosscheck:
	@echo "=== prose vs recorded output ==="
	@$(PY314) -m _harness.crosscheck $(CH)

# Deliberately not a dependency of anything. Re-recording expected output is how
# a drifted transcript gets silently blessed, so it is always an explicit act.
record:
	@$(PY313) -m _harness.verify --record $(CH)
	@$(PY314) -m _harness.verify --record $(CH)
	@echo ""
	@echo "Expected output regenerated. Review 'git diff' before committing:"
	@echo "a change here means the interpreter changed, or the listing did."

# Free-threaded recordings are per-chapter and explicit: only chapters that
# target the t-build record output for it. Requires CH=chNNN.
record-314t:
	@test -n "$(CH)" || { echo "record-314t requires CH=chNNN"; exit 1; }
	@$(PY314T) -m _harness.verify --record $(CH)

bench:
	@for f in $(wildcard $(if $(CH),$(CH),ch*)/bench_*.py); do \
		echo "=== $$f ==="; $(PY313) $$f; echo; \
	done

interpreters:
	@$(PY313) -m _harness.interpreters
	@$(PY314) -m _harness.interpreters
	@if [ -x "$(PY314T)" ]; then $(PY314T) -m _harness.interpreters; fi

clean:
	@find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
