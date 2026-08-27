.PHONY: install test bench lint

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

bench:
	$(PYTHON) benchmarks/bench_modal.py
	$(PYTHON) benchmarks/bench_updating.py

lint:
	$(PYTHON) -m ruff check .
