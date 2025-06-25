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

### Development
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