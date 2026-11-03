PYTHON ?= python3

.PHONY: generate validate database analyze test all

generate:
	$(PYTHON) struct.py generate

validate:
	$(PYTHON) struct.py validate

database:
	$(PYTHON) struct.py build-db

analyze:
	$(PYTHON) struct.py analyze

test:
	$(PYTHON) struct.py test

all:
	$(PYTHON) struct.py run-all
