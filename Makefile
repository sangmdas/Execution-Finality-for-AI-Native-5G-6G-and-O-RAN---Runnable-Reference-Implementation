.PHONY: install test demo replay benchmark examples clean

install:
	python -m pip install -e '.[dev]'

test:
	pytest -q

demo:
	python -m network_finality.cli

replay:
	python -m network_finality.cli --replay

benchmark:
	python scripts/benchmark.py --iterations 1000

examples:
	python scripts/generate_examples.py

clean:
	rm -rf .pytest_cache .ef-state build dist *.egg-info src/*.egg-info
