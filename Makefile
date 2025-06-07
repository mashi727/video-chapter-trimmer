.PHONY: help install install-dev test lint type-check format clean build upload

help:
	@echo "Available commands:"
	@echo "  install       Install the package"
	@echo "  install-dev   Install with development dependencies"
	@echo "  test          Run tests"
	@echo "  lint          Run linters"
	@echo "  type-check    Run type checking"
	@echo "  format        Format code"
	@echo "  clean         Clean build artifacts"
	@echo "  build         Build distribution packages"
	@echo "  upload        Upload to PyPI"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev]"
	pre-commit install

test:
	pytest -v

test-cov:
	pytest --cov=video_chapter_trimmer --cov-report=term-missing --cov-report=html

lint:
	black --check src tests
	isort --check-only src tests
	flake8 src tests
	pylint src

type-check:
	mypy src

format:
	black src tests
	isort src tests

clean:
	rm -rf build dist *.egg-info
	rm -rf .coverage htmlcov .pytest_cache
	rm -rf .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: clean
	python -m build

upload: build
	python -m twine upload dist/*

upload-test: build
	python -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*