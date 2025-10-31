PY?=python3
# Try to find Python 3.11+ if available
PY311=$(shell which python3.11 2>/dev/null || which python3.12 2>/dev/null || which python3.13 2>/dev/null || echo python3)
ifeq ($(shell $(PY311) -c "import sys; print('OK' if sys.version_info >= (3, 11) else 'FAIL')" 2>/dev/null),OK)
    PY=$(PY311)
endif
UV?=uv
APP=src/iva/server.py
PORT?=8080

.PHONY: check-python
check-python:
	@echo "Using Python: $(PY)"
	@$(PY) -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)" || \
		(echo "❌ Error: Python 3.11+ required. Current: $$($(PY) --version 2>&1)" && \
		 echo "Install Python 3.11+ with: brew install python@3.11" && exit 1)

dev: check-python
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) pip install -r requirements.txt; \
	else \
		$(PY) -m pip install -r requirements.txt; \
	fi
	$(PY) -m playwright install --with-deps chromium

playwright:
	$(PY) -m playwright install chromium

run: check-python
	$(PY) -m uvicorn src.iva.server:app --host 0.0.0.0 --port $(PORT) --reload

cli: check-python
	$(PY) -m src.iva.cli verify --url "$(URL)" --company "$(COMPANY)" --jurisdiction US

db:
	$(PY) scripts/load_golden.py

test:
	PYTHONPATH=. $(PY) -m pytest -q

lint:
	$(PY) -m ruff check .

format:
	$(PY) -m ruff format .
