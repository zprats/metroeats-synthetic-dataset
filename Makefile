PYTHON ?= python3

.PHONY: generate validate database analyze catalogue test all

generate:
	$(PYTHON) struct.py generate

validate:
	$(PYTHON) struct.py validate

database:
	$(PYTHON) struct.py build-db

analyze:
	$(PYTHON) struct.py analyze

catalogue:
	$(PYTHON) struct.py build-catalogue

test:
	$(PYTHON) struct.py test

all:
	$(PYTHON) struct.py run-all
