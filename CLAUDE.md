# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`claude-notes` is a Python CLI tool that transforms Claude Code's transcript JSONL files into terminal-viewable output and HTML files. The tool is built with `uv` for fast Python package management and is designed to be runnable with `uvx` for easy distribution and usage.

## Technology Stack

- **Python 3.11+** - Main programming language
- **uv** - Fast Python package and project manager
- **uvx** - Tool for running Python applications in isolated environments
- **CLI Framework** - To be determined (likely Click or Typer)

## Development Setup

1. Install `uv` if not already installed: `curl -LsSf https://astral.sh/uv/install.sh | sh`
2. Initialize the project environment: `uv sync`
3. Run the CLI in development: `uv run claude-notes`

## Common Commands

### Using Make (Recommended)
The project includes a Makefile with essential development commands:

```bash
make build         # Build the package
make format        # Format code with ruff
make test          # Run tests and CLI functionality check
```

### Direct UV Commands
- **Install dependencies**: `uv sync`
- **Add a dependency**: `uv add <package>`
- **Add a dev dependency**: `uv add --dev <package>`
- **Run tests**: `uv run pytest` (when tests are added)
- **Format code**: `uv run ruff format`
- **Lint code**: `uv run ruff check`

### CLI Usage

```bash
# List all Claude projects
uv run claude-notes list-projects

# Show transcripts for current directory (with pager)
uv run claude-notes .

# Show transcripts for specific project
uv run claude-notes /path/to/project

# Show all content at once without pager
uv run claude-notes . --no-pager

# Show raw JSON data
uv run claude-notes . --raw

# Run with uvx (after publishing)
uvx claude-notes .
```

### Pager Controls

The default view uses a `less`-like pager interface:

- **ENTER/SPACE** - Next page
- **j** - Next line  
- **k** - Previous line
- **b** - Previous page
- **g** - Go to top
- **G** - Go to bottom
- **h** - Show help
- **q** - Quit

## Project Structure

The project will be organized as follows:
- `src/claude_notes/` - Main package directory
  - `__main__.py` - Entry point for the CLI
  - `cli.py` - CLI command definitions
  - `parser.py` - JSONL parsing logic
  - `formatters/` - Output formatters (terminal, HTML)
- `tests/` - Test files
- `pyproject.toml` - Project configuration and dependencies

## Architecture Notes

The tool processes Claude Code transcript JSONL files which contain conversation data. Key components:

1. **JSONL Parser**: Reads and parses Claude Code transcript files
2. **Formatters**: Transform parsed data into different output formats
   - Terminal formatter: Rich text output for terminal viewing
   - HTML formatter: Generates standalone HTML files
3. **CLI Interface**: Provides commands for different output options

## Input/Output

- **Input**: Claude Code transcript JSONL files (typically from `~/.claude/conversations/`)
- **Output**: 
  - Terminal-formatted text (with syntax highlighting, formatting)
  - HTML files (with styling, code blocks, conversation structure)

## Git Workflow

This project follows a structured Git workflow to maintain code quality and enable collaboration:

### Branch Strategy
- **Main branch**: `main` - stable, production-ready code
- **Feature branches**: `feature/description` or `fix/description` - for all changes
- Never commit directly to `main` - always use pull requests

### Development Process

1. **Create feature branch**:
   ```bash
   git checkout main
   git pull origin main
   git checkout -b feature/add-new-formatter
   ```

2. **Make changes with frequent commits**:
   ```bash
   # Make logical changes
   uv run ruff format  # Format code
   uv run ruff check   # Lint code
   git add .
   git commit -m "feat: add basic HTML formatter structure"
   
   # Continue with more changes
   # Commit after each logical change
   git commit -m "feat: implement HTML message formatting"
   git commit -m "style: add CSS styling for HTML output"
   git commit -m "test: verify HTML formatter works correctly"
   ```

3. **Before each commit, always run**:
   ```bash
   make format           # Format code
   make test             # Test functionality
   uv run ruff check     # Check for linting issues
   ```

4. **Push and create PR**:
   ```bash
   git push origin feature/add-new-formatter
   # Create pull request on GitHub
   ```

### Commit Message Convention

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Build/tooling changes

**Examples:**
```bash
git commit -m "feat: add HTML export functionality"
git commit -m "fix: handle empty conversation files gracefully"
git commit -m "docs: update README with installation instructions"
git commit -m "style: format code with ruff"
git commit -m "refactor: extract formatter base class"
git commit -m "test: add unit tests for JSONL parser"
git commit -m "chore: update dependencies in pyproject.toml"
```

### Quality Gates

Before committing:
1. ✅ Code is formatted with `make format`
2. ✅ No linting errors from `uv run ruff check`
3. ✅ CLI tool runs without errors with `make test`
4. ✅ Commit follows conventional commit format
5. ✅ Commit represents one logical change

### Pre-commit Hooks (Optional)

Install pre-commit hooks to automate quality checks:
```bash
uv add --dev pre-commit
uv run pre-commit install
```

This will automatically run formatting and linting before each commit.