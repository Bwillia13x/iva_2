PY=python
UV?=uv
APP=src/iva/server.py
PORT?=8080

dev:
	@if command -v $(UV) >/dev/null 2>&1; then \
		$(UV) pip install -r requirements.txt; \
	else \
		$(PY) -m pip install -r requirements.txt; \
	fi
	$(PY) -m playwright install --with-deps chromium

playwright:
	$(PY) -m playwright install chromium

run:
	$(PY) -m uvicorn src.iva.server:app --host 0.0.0.0 --port $(PORT) --reload

cli:
	$(PY) -m src.iva.cli verify --url "$(URL)" --company "$(COMPANY)" --jurisdiction US

db:
	$(PY) scripts/load_golden.py

test:
	PYTHONPATH=. pytest -q

lint:
	ruff check .

format:
	ruff format .
