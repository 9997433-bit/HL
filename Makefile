.PHONY: install test bench lint

install:
	python -m pip install -e ".[dev]"

test:
	python -m pytest

bench:
	python benchmarks/bench_modal.py
	python benchmarks/bench_updating.py

lint:
	python -m ruff check .
