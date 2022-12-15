SHELL:=/bin/bash

PYTHON_VERSION:=$(shell cat .python-version)
PYTHON_SHORT_VERSION:=$(shell cat .python-version | grep -o '[0-9].[0-9]*')
MIGRATION_DATABASE:=./migrate.db

ifndef USE_SYSTEM_PYTHON
	ifdef CI
		USE_SYSTEM_PYTHON:=true
	endif
endif

ifeq ($(USE_SYSTEM_PYTHON), true)
	PYTHON_PACKAGE_PATH:=$(shell python -c "import sys; print(sys.path[-1])")
	PYTHON := python
	PYTHON_VENV :=
	PYTHON_PYENV :=
else
	PYTHON_PACKAGE_PATH:=.venv/lib/python$(PYTHON_SHORT_VERSION)/site-packages
	PYTHON := . .venv/bin/activate && python
	PYTHON_VENV := .venv
	PYTHON_PYENV := pyenv
endif

# Used to confirm that pip has run at least once
PACKAGE_CHECK:=$(PYTHON_PACKAGE_PATH)/piptools
PYTHON_DEPS := $(PACKAGE_CHECK)

.PHONY: all
all: $(PACKAGE_CHECK)

.PHONY: install
install: $(PYTHON_PYENV) $(PYTHON_VENV) pip

.venv:
	python -m venv .venv

.PHONY: pyenv
pyenv:
	pyenv install --skip-existing $(PYTHON_VERSION)

pip: $(PYTHON_VENV)
	$(PYTHON) -m pip install -e .[dev]

$(PACKAGE_CHECK): $(PYTHON_VENV)
	$(PYTHON) -m pip install -e .[dev]

#
# Application Specific
#
PHONY: big_crawl
big_crawl:
	. .venv/bin/activate && NUM_PROCESSES=50 LOOKUP_BLOCK_SIZE=200 python -m fedimapper.run

PHONY: medium_crawl
medium_crawl:
	. .venv/bin/activate && NUM_PROCESSES=25 LOOKUP_BLOCK_SIZE=100 python -m fedimapper.run


#
# Formatting
#

.PHONY: pretty
pretty: $(PYTHON_DEPS)
	$(PYTHON) -m black . && \
	isort .

.PHONY: black_fixes
black_fixes: $(PYTHON_DEPS)
	$(PYTHON) -m black .

.PHONY: isort_fixes
isort_fixes: $(PYTHON_DEPS)
	$(PYTHON) -m isort .


#
# Testing
#

.PHONY: tests
tests: install pytest isort_check black_check mypy_check

.PHONY: pytest
pytest: $(PYTHON_DEPS)
	$(PYTHON) -m pytest --cov=./fedimapper --cov-report=term-missing tests

.PHONY: pytest_loud
pytest_loud: $(PYTHON_DEPS)
	$(PYTHON) -m pytest -s --cov=./fedimapper --cov-report=term-missing tests

.PHONY: isort_check
isort_check: $(PYTHON_DEPS)
	$(PYTHON) -m isort --check-only .

.PHONY: black_check
black_check: $(PYTHON_DEPS)
	$(PYTHON) -m black . --check

.PHONY: mypy_check
mypy_check: $(PYTHON_DEPS)
	$(PYTHON) -m mypy fedimapper


#
# Dependencies
#

.PHONY: rebuild_dependencies
rebuild_dependencies:
	$(PYTHON) -m piptools compile --output-file=requirements.txt pyproject.toml
	$(PYTHON) -m piptools compile --output-file=requirements-dev.txt --extra=dev pyproject.toml

.PHONY: dependencies
dependencies: requirements.txt requirements-dev.txt

requirements.txt: $(PYTHON_DEPS) pyproject.toml
	$(PYTHON) -m piptools compile --upgrade --output-file=requirements.txt pyproject.toml

requirements-dev.txt: $(PYTHON_DEPS) pyproject.toml
	$(PYTHON) -m piptools compile --upgrade --output-file=requirements-dev.txt --extra=dev pyproject.toml


#
# Packaging
#

.PHONY: build
build: $(PYTHON_DEPS)
	$(PYTHON) -m build


#
# Migrations
#


.PHONY: run_migrations
run_migrations:
	$(PYTHON) -m alembic upgrade head

reset_db: clear_db run_migrations

clear_db:
	rm -Rf test.db*

.PHONY: create_migration
create_migration:
	@if [ -z "$(MESSAGE)" ]; then echo "Please add a message parameter for the migration (make create_migration MESSAGE=\"database migration notes\")."; exit 1; fi
	rm $(MIGRATION_DATABASE) | true
	. .venv/bin/activate && DATABASE_URL=sqlite:///$(MIGRATION_DATABASE) python -m alembic upgrade head
	. .venv/bin/activate && DATABASE_URL=sqlite:///$(MIGRATION_DATABASE) python -m alembic revision --autogenerate -m "$(MESSAGE)"
	rm $(MIGRATION_DATABASE)
