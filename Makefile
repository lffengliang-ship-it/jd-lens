PYTHON ?= python

.PHONY: test analyze

test:
	$(PYTHON) -m unittest discover -s tests

analyze:
	$(PYTHON) -m src.run_analyze
