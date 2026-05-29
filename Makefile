init_project:
	git init
	uv sync
	uv run pre-commit install
	uv run pre-commit install --hook-type commit-msg

python_src:
	export PYTHONPATH=$(PWD)

verify:
	uv run ruff check src tests
	uv run ruff format --check src tests
	uv run pytest tests -q
	cd frontend && CI=true npm test -- --watchAll=false

## Delete all compiled Python files
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
