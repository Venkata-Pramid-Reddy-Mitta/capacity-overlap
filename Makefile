# All targets run offline. `make verify` is the single promise the README makes to a reviewer.
.PHONY: install lint test coverage experiments receipts evidence verify clean generate

PY ?= python

install:
	$(PY) -m pip install -e ".[dev]"

lint:
	$(PY) -m ruff check src tests experiments tools
	$(PY) -m ruff format --check src tests experiments tools

test:
	$(PY) -m pytest --junitxml=junit.xml --cov=capacity_overlap --cov-report=xml --cov-report=json --cov-report=term-missing

coverage:
	$(PY) tools/check_coverage.py --floor 95

experiments:
	$(PY) experiments/exp_hidden_vs_sprint.py
	$(PY) experiments/exp_aggregation_window.py
	$(PY) experiments/exp_threshold_sensitivity.py
	$(PY) experiments/exp_workstream_attribution.py

receipts:
	$(PY) tools/collect_metrics.py --skip-tests
	$(PY) tools/check_numbers.py

# Regenerate the committed plan fixture from its seed. Not part of verify: the fixture is committed.
generate:
	$(PY) -m capacity_overlap.cli generate --seed 20260410 --out data/plan.csv

# Evidence needs the optional [evidence] extra and a Chromium; it is not required for verify.
evidence:
	$(PY) tools/render_diagrams.py
	$(PY) tools/capture_screenshots.py
	$(PY) tools/record_demo.py

verify: lint test coverage experiments receipts
	@echo "verify: OK"

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov coverage.xml coverage.json junit.xml .coverage reports
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
