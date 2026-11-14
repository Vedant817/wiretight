# Wiretight — FINAL.md §6.5
#
# Targets marked (*) hit the real Airwallex sandbox and exit 2 unless
# CONFIRM_LIVE=1 is set. There is no way to reach the sandbox from a plain
# `make test`; offline is the default and CI never has credentials.
#
#   make setup && make test && make demo DEMO_MODE=replay
#
# Run `make help` for the list.

SHELL := /bin/sh
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help
.DELETE_ON_ERROR:
MAKEFLAGS += --no-builtin-rules

UV ?= uv
PY := $(UV) run --frozen python
UVRUN := $(UV) run --frozen

export PYTHONDONTWRITEBYTECODE := 1

# --------------------------------------------------------------------------
# Live-target gate
# --------------------------------------------------------------------------
# require_live <target-name>: refuse to touch the sandbox without explicit intent.
define require_live
	@if [ "$(CONFIRM_LIVE)" != "1" ]; then \
		echo "REFUSING: $(1) calls the real Airwallex SANDBOX." >&2; \
		echo "Re-run with CONFIRM_LIVE=1 when you mean it." >&2; \
		exit 2; \
	fi
endef

.PHONY: help
help:
	@echo 'Wiretight — see docs/spec/FINAL.md section 6.5'
	@echo 
	@echo   setup            install deps, generate local keys, install hooks
	@echo   keys             generate Ed25519 audit key + approver HMAC keys
	@echo   hooks            install the pre-commit secret hook
	@echo   lint             ruff check + format check
	@echo   fmt              ruff format (writes)
	@echo   typecheck        mypy
	@echo   test             offline: unit + property + contract + acceptance
	@echo   test-cov         the same, with a coverage report
	@echo   calendars        regenerate app/core/calendars/*.yaml
	@echo   seed-local       seed vendors/contacts/history into the local ledger
	@echo   eval             20 labelled scenarios over FakeAirwallex
	@echo   eval-selftest    disable each control, prove the metrics drop
	@echo   verify-audit     verify the audit chain against signed checkpoints
	@echo   serve            web process (LLM key, no Airwallex key)
	@echo   worker           executor + poller (Airwallex key, no LLM key)
	@echo   demo             DEMO_MODE=replay|live
	@echo   shadow-report    the would-have-caught report for RUN=<id>
	@echo   package          dist/wiretight-src.zip, no .env, no var/
	@echo   ci               lint test eval eval-selftest verify-audit
	@echo 
	@echo   (*) needs CONFIRM_LIVE=1 and real sandbox credentials:
	@echo       test-live  eval-live  spike  fixtures-record  seed  passkeys  sign-policy

.PHONY: setup
setup: keys
	$(UV) sync --frozen --extra dev
	@echo 
	@echo Ready. Offline path:   make test
	@echo         Sandbox path:  put your keys in .env, then CONFIRM_LIVE=1 make spike

.PHONY: keys
keys:
	$(PY) -c "from pathlib import Path; Path('var/keys').mkdir(parents=True, exist_ok=True)"
	$(PY) scripts/generate_keys.py

.PHONY: hooks
hooks:
	$(PY) scripts/install_hooks.py

# --------------------------------------------------------------------------
# Quality
# --------------------------------------------------------------------------
.PHONY: lint
lint:
	$(UVRUN) ruff check app scripts tests eval
	$(UVRUN) ruff format --check app scripts tests eval

.PHONY: fmt
fmt:
	$(UVRUN) ruff format app scripts tests eval
	$(UVRUN) ruff check --fix app scripts tests eval

.PHONY: typecheck
typecheck:
	$(UVRUN) mypy app

# --------------------------------------------------------------------------
# Tests — always offline. conftest.py blocks sockets (§10.1 rule 9).
# --------------------------------------------------------------------------
.PHONY: test
test:
	$(UVRUN) pytest tests/unit tests/property tests/contract tests/acceptance -q

.PHONY: test-cov
test-cov:
	$(UVRUN) pytest tests/unit tests/property tests/contract tests/acceptance -q \
		--cov=app --cov-report=term-missing --cov-report=xml

.PHONY: test-live
test-live:
	$(call require_live,test-live)
	$(UVRUN) pytest tests/live -q -m live

.PHONY: test-all
test-all:
	$(UVRUN) pytest -q

# --------------------------------------------------------------------------
# Day-1 sandbox spike and fixtures (§9). Recording is local and never in CI.
# --------------------------------------------------------------------------
.PHONY: spike
spike:
	$(call require_live,spike)
	$(PY) scripts/day1_spike.py

.PHONY: fixtures-record
fixtures-record:
	$(call require_live,fixtures-record)
	$(PY) scripts/record_fixtures.py

.PHONY: fixtures-check
fixtures-check:
	$(PY) scripts/check_fixtures.py

.PHONY: calendars
calendars:
	$(PY) scripts/gen_calendars.py

# --------------------------------------------------------------------------
# Seeding (§8.6)
# --------------------------------------------------------------------------
.PHONY: seed-local
seed-local:
	$(PY) scripts/seed_local.py

.PHONY: seed
seed:
	$(call require_live,seed)
	$(PY) scripts/seed_sandbox.py

# --------------------------------------------------------------------------
# Evaluation (§10.4)
# --------------------------------------------------------------------------
.PHONY: eval
eval:
	$(UVRUN) pytest eval -q

.PHONY: eval-selftest
eval-selftest:
	$(UV) run --frozen python -m eval.selftest

.PHONY: eval-live
eval-live:
	$(call require_live,eval-live)
	$(UV) run --frozen python -m eval.harness --live

# --------------------------------------------------------------------------
# Runtime. `env -u` keeps each process blind to the other's secret (§5.3).
# --------------------------------------------------------------------------
.PHONY: serve
serve:
	env -u AWX_CLIENT_ID -u AWX_API_KEY $(UV) run --frozen uvicorn app.api.main:app \
		--host $${APP_HOST:-127.0.0.1} --port $${APP_PORT:-8000}

.PHONY: worker
worker:
	env -u ANTHROPIC_API_KEY $(PY) -m app.workers.run

.PHONY: demo
demo:
	$(PY) scripts/run_demo.py

# The labelled demo mode for the pitch recording: simulated data throughout,
# mocked Airwallex responses. DEMO_MODE=video is required so demo mode is a
# deliberate act.
.PHONY: demo-video
demo-video:
	env -u AWX_CLIENT_ID -u AWX_API_KEY DEMO_MODE=video $(PY) -m tests.support.recording.server \
		--port $${DEMO_PORT:-8765}

.PHONY: shadow-report
shadow-report:
	$(PY) -m app.core.shadow --run $(RUN)

.PHONY: verify-audit
verify-audit:
	$(PY) -m app.cli verify-audit

# --------------------------------------------------------------------------
# Human-only targets. These need a passkey gesture on localhost.
# --------------------------------------------------------------------------
.PHONY: passkeys
passkeys:
	$(call require_live,passkeys)
	$(PY) scripts/register_passkeys.py

.PHONY: sign-policy
sign-policy:
	$(call require_live,sign-policy)
	$(PY) scripts/sign_policy.py

# --------------------------------------------------------------------------
# Packaging and CI
# --------------------------------------------------------------------------
.PHONY: package
package: verify-audit
	@$(PY) scripts/package.py

.PHONY: ci
ci: lint test eval eval-selftest verify-audit
	@echo CI green.

.PHONY: clean
clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .hypothesis .coverage coverage.xml
	rm -rf dist build *.egg-info
	find . -name '__pycache__' -type d -prune -exec rm -rf {} +