# Architecture

## Overview

`claude-notes` is a Python CLI tool that transforms Claude Code transcript JSONL files into human-readable formats: terminal output with Rich formatting, standalone HTML files, and animated GIF/MP4 recordings.

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| Package Manager | uv (with uvx for distribution) |
| CLI Framework | Click |
| Terminal Formatting | Rich |
| Build System | Hatchling |
| Linting/Formatting | Ruff |
| CI/CD | GitHub Actions |

## Directory Structure

```
claude-notes/
├── src/claude_notes/           # Main package
│   ├── __init__.py             # Package metadata (version)
│   ├── __main__.py             # Entry point, handles Windows encoding
│   ├── cli.py                  # CLI commands (list-projects, show)
│   ├── parser.py               # JSONL transcript parser
│   ├── pager.py                # Terminal pager (less-like interface)
│   └── formatters/             # Output formatters
│       ├── __init__.py         # Public exports
│       ├── base.py             # Abstract base class, tool result collection
│       ├── factory.py          # Formatter factory pattern
│       ├── terminal.py         # Rich terminal output
│       ├── html.py             # Standalone HTML generation
│       ├── animated.py         # Asciicast/GIF/MP4 generation
│       └── tools.py            # Tool-specific formatters (Bash, Read, Edit, etc.)
├── examples/                   # Example outputs
├── .github/workflows/ci.yml    # CI pipeline
├── pyproject.toml              # Project config, dependencies, ruff settings
├── Makefile                    # build, format, test commands
└── CLAUDE.md                   # AI assistant guidance
```

## Core Components

### 1. CLI (`cli.py`)

The main interface with two commands:
- `list-projects`: Lists all Claude projects from `~/.claude/projects/`
- `show`: Displays conversations for a project path

Key responsibilities:
- Path encoding/decoding for Claude's folder naming scheme
- Session and message ordering (asc/desc)
- Format selection (terminal, html, animated)
- Output file handling

### 2. Parser (`parser.py`)

`TranscriptParser` class that:
- Reads JSONL files line by line
- Extracts conversation metadata (timestamps, session IDs)
- Provides message iteration

### 3. Formatters (`formatters/`)

**Base Class (`base.py`)**
- `BaseFormatter`: Abstract class defining the interface
- `_collect_tool_results()`: Maps tool results to their parent tool uses
- `_group_messages()`: Groups consecutive messages by role

**Terminal Formatter (`terminal.py`)**
- Uses Rich for styled console output
- Renders Markdown content
- Handles special tags (`<command-message>`, `<system-reminder>`)

**HTML Formatter (`html.py`)**
- Generates standalone HTML with embedded CSS
- Includes navigation (TOC, anchors, back-to-top)
- Humanizes timestamps
- Supports custom CSS via `--style` option

**Animated Formatter (`animated.py`)**
- Generates asciicast files for asciinema
- Converts to GIF via `agg`
- Converts to MP4 via `ffmpeg`
- Supports typing speed, pause duration, max duration limits
- Emoji fallback mappings for GIF compatibility

**Tool Formatters (`tools.py`)**
- Specialized formatters for each tool type:
  - `BashFormatter`: Commands with truncated output
  - `ReadFormatter`: File reads with line counts
  - `WriteFormatter`: File writes with diff preview
  - `EditFormatter`/`MultiEditFormatter`: Structured patch display
  - `GrepFormatter`: Search results with match counts
  - `TaskFormatter`: Delegated task display
  - `TodoReadFormatter`/`TodoWriteFormatter`: Todo list display

### 4. Pager (`pager.py`)

Terminal pager with `less`-like controls:
- Page navigation (space, b)
- Line navigation (j, k)
- Jump to top/bottom (g, G)
- Cross-platform (Unix termios, Windows msvcrt)

## Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI (cli.py)                            │
│  1. Parse arguments                                             │
│  2. Find project folder (encode/decode path)                    │
│  3. List JSONL files                                            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Parser (parser.py)                           │
│  1. Read JSONL lines                                            │
│  2. Parse JSON objects                                          │
│  3. Extract metadata (timestamps, session IDs)                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Formatter (formatters/)                        │
│  1. Collect tool results                                        │
│  2. Group messages by role                                      │
│  3. Format each message group                                   │
│  4. Apply tool-specific formatting                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Output                                     │
│  - Terminal: Rich console (with optional pager)                 │
│  - HTML: Standalone file with embedded CSS                      │
│  - Animated: .cast → .gif/.mp4                                  │
└─────────────────────────────────────────────────────────────────┘
```

## External Integrations

| Integration | Purpose |
|-------------|---------|
| `~/.claude/projects/` | Source of transcript JSONL files |
| `agg` | Asciicast to GIF conversion (optional) |
| `ffmpeg` | GIF/SVG to MP4 conversion (optional) |
| `svg-term-cli` | Higher quality MP4 via SVG (optional) |

## Configuration

### pyproject.toml
- Project metadata and dependencies
- Ruff linting rules (E, W, F, I, B, C4, UP)
- Line length: 120
- Quote style: double

### .pre-commit-config.yaml
- Ruff formatting and linting
- File hygiene (trailing whitespace, YAML/TOML validation)

### Environment Variables
- `PYTHONIOENCODING`: UTF-8 fallback for Windows

## Build & Deploy

```bash
# Development
uv sync                    # Install dependencies
uv run claude-notes show . # Run locally

# Quality checks
make format                # Format with ruff
uv run ruff check          # Lint
make test                  # CLI functionality check

# Build
make build                 # Creates dist/

# Release (via GitHub Actions)
# Tag with v* triggers PyPI publish
git tag v0.1.5 && git push --tags
```

## Optional Dependencies

```bash
# Animation support
uv add --optional-deps animation  # Adds asciinema

# External tools for animation
brew install agg                  # GIF generation
brew install ffmpeg               # MP4 generation
npm install -g svg-term-cli       # Higher quality MP4
```
