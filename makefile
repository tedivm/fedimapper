SHELL:=/bin/bash

PYTHON_VERSION:=$(shell cat .python-version)
PYTHON_SHORT_VERSION:=$(shell cat .python-version | grep -o '[0-9].[0-9]*')
MIGRATION_DATABASE:=./migrate.db

ifdef CI
	PYTHON_PYENV :=
else
	PYTHON_PYENV := pyenv
endif

ifeq ($(USE_SYSTEM_PYTHON), true)
	PYTHON_PACKAGE_PATH:=$(shell python -c "import sys; print(sys.path[-1])")
	PYTHON := python
	PYTHON_VENV :=
else
	PYTHON_PACKAGE_PATH:=.venv/lib/python$(PYTHON_SHORT_VERSION)/site-packages
	PYTHON := . .venv/bin/activate && python
	PYTHON_VENV := .venv
endif

# Used to confirm that pip has run at least once
PACKAGE_CHECK:=$(PYTHON_PACKAGE_PATH)/piptools
PYTHON_DEPS := $(PACKAGE_CHECK)

.PHONY: all
all: $(PACKAGE_CHECK) data/stop-words

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
	$(PYTHON) -m fedimapper.cli crawl --num-processes=50

PHONY: medium_crawl
medium_crawl:
	$(PYTHON) -m fedimapper.cli crawl --num-processes=25


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

requirements.txt: $(PYTHON_DEPS) pyproject.toml setup.cfg
	$(PYTHON) -m piptools compile --upgrade --output-file=requirements.txt pyproject.toml

requirements-dev.txt: $(PYTHON_DEPS) pyproject.toml setup.cfg
	$(PYTHON) -m piptools compile --upgrade --output-file=requirements-dev.txt --extra=dev pyproject.toml

#
# Data Dependencies
#

.PHONY: build_data
build_data: data/stop-words

data:
	mkdir data

data/stop-words: data
	git clone https://github.com/Alir3z4/stop-words data/stop-words

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

.PHONY: reset_db
reset_db: clear_db run_migrations

.PHONY: clear_db
clear_db:
	rm -Rf test.db*

.PHONY: vacuum_db
vacuum_db:
	$(PYTHON) -m fedimapper.cli vacuum-database

.PHONY: create_migration
create_migration:
	@if [ -z "$(MESSAGE)" ]; then echo "Please add a message parameter for the migration (make create_migration MESSAGE=\"database migration notes\")."; exit 1; fi
	rm $(MIGRATION_DATABASE) | true
	. .venv/bin/activate && DATABASE_URL=sqlite:///$(MIGRATION_DATABASE) python -m alembic upgrade head
	. .venv/bin/activate && DATABASE_URL=sqlite:///$(MIGRATION_DATABASE) python -m alembic revision --autogenerate -m "$(MESSAGE)"
	rm $(MIGRATION_DATABASE)
	$(PYTHON) -m isort ./db
	$(PYTHON) -m black ./db

