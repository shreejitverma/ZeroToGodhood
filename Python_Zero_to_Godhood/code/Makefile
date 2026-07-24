# Verification and measurement entry points for Python Zero to Godhood, Book II.
#
# The book's central claim is that every "Verified output" block in the prose
# was produced by a program in this tree. `make verify` is what makes that
# claim checkable rather than aspirational.

PY313 ?= /opt/anaconda3/bin/python3
PY314 ?= python3
CH    ?=

.PHONY: help verify verify-313 verify-314 crosscheck record bench interpreters clean

help:
	@echo "make verify        - listings on both interpreters, then prose cross-check"
	@echo "make crosscheck    - check output quoted in the prose matches the listings"
	@echo "make verify-313    - check on CPython 3.13 only"
	@echo "make verify-314    - check on CPython 3.14 only"
	@echo "make record        - regenerate expected output (review the diff before committing)"
	@echo "make bench         - run benchmarks (results are never auto-committed)"
	@echo "make interpreters  - report the verification matrix and flag build mismatches"
	@echo ""
	@echo "Restrict to one chapter with CH=ch18, e.g. 'make verify CH=ch18'"

verify: verify-313 verify-314 crosscheck

verify-313:
	@echo "=== CPython 3.13 ==="
	@$(PY313) -m _harness.verify $(CH)

verify-314:
	@echo "=== CPython 3.14 ==="
	@$(PY314) -m _harness.verify $(CH)

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

bench:
	@for f in $(wildcard $(if $(CH),$(CH),ch*)/bench_*.py); do \
		echo "=== $$f ==="; $(PY313) $$f; echo; \
	done

interpreters:
	@$(PY313) -m _harness.interpreters
	@$(PY314) -m _harness.interpreters

clean:
	@find . -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true
