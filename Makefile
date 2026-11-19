.PHONY: run test lint fmt install migrate createsuperuser

install:
	uv sync --dev

run:
	uv run python manage.py runserver

test:
	uv run pytest

lint:
	uv run ruff check src tests
	uv run mypy src

fmt:
	uv run ruff format src tests

migrate:
	uv run python manage.py migrate

createsuperuser:
	uv run python manage.py createsuperuser
