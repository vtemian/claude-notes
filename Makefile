# Makefile for claude-notes
# Provides the three essential development commands

.PHONY: build format test

build: ## Build the package
	uv build

format: ## Format code with ruff
	uv run ruff format

test: ## Run tests and basic CLI functionality check
	@echo "Running basic CLI functionality test..."
	uv run claude-notes --help > /dev/null
	@echo "✅ CLI functionality verified"
	@echo "Note: Add 'uv run pytest' here when unit tests are created"