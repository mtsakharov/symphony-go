UV ?= uv

.PHONY: sync run test lint fmt typecheck migrate

sync:
	$(UV) sync

run:
	$(UV) run serve

test:
	$(UV) run pytest

lint:
	$(UV) run ruff check .

fmt:
	$(UV) run ruff format .

typecheck:
	$(UV) run mypy src tests

migrate:
	$(UV) run alembic upgrade head
