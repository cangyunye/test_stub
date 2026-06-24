VENV = .venv
PYTHON = $(VENV)/bin/python
PORT ?= 8080

.PHONY: install run test lint clean

install:
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install -e ".[dev]" -q

run:
	$(PYTHON) -m mock_server start --port $(PORT)

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m pip install -q ruff
	$(PYTHON) -m ruff check src/

clean:
	rm -rf $(VENV) *.db __pycache__ .pytest_cache
	find . -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
