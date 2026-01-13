# Code Style Guide

## Naming Conventions

### Files
- **Modules**: `snake_case.py` (e.g., `parser.py`, `cli.py`, `base.py`)
- **Package directories**: `snake_case` (e.g., `claude_notes`, `formatters`)

### Classes
- **PascalCase**: `TranscriptParser`, `TerminalFormatter`, `HTMLBashFormatter`
- **Suffix pattern for formatters**: `{Format}{Tool}Formatter` (e.g., `HTMLEditFormatter`)
- **Base classes**: Prefix with `Base` (e.g., `BaseFormatter`)

### Functions and Methods
- **snake_case**: `get_messages()`, `format_conversation()`, `_collect_tool_results()`
- **Private methods**: Single underscore prefix (e.g., `_parse()`, `_display_header()`)
- **CLI commands**: Kebab-case in Click (e.g., `list-projects`), snake_case in Python

### Variables
- **snake_case**: `file_path`, `tool_result`, `message_parts`
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `TOOL_FORMATTERS`, `EMOJI_FALLBACKS`)

## File Organization

### Module Structure
```python
"""Module docstring - one line description."""

# Standard library imports
import json
from pathlib import Path
from typing import Any

# Third-party imports
import click
from rich.console import Console

# Local imports
from claude_notes.formatters.base import BaseFormatter
```

### Class Structure
```python
class ClassName:
    """Class docstring."""

    def __init__(self, ...):
        """Initialize with parameters."""
        pass

    # Public methods first
    def public_method(self) -> ReturnType:
        """Method docstring."""
        pass

    # Private methods after
    def _private_method(self) -> ReturnType:
        """Private method docstring."""
        pass
```

## Import Style

1. **Group order**: stdlib → third-party → local
2. **Blank line** between groups
3. **Alphabetical** within groups (enforced by ruff isort)
4. **Explicit imports**: Prefer `from module import Class` over `import module`

```python
# Good
from pathlib import Path
from typing import Any

import click
from rich.console import Console

from claude_notes.formatters.base import BaseFormatter

# Avoid
import os, sys  # Multiple imports on one line
from claude_notes import *  # Star imports
```

## Code Patterns

### Type Hints
Always use type hints for function signatures:
```python
def format_conversation(
    self, 
    messages: list[dict[str, Any]], 
    conversation_info: dict[str, Any]
) -> str:
```

Use `|` for union types (Python 3.10+):
```python
def find_project_folder(project_path: Path) -> Path | None:
```

### Docstrings
Use Google-style docstrings:
```python
def format_tool_use(self, tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
    """Format a tool use with its result.

    Args:
        tool_name: Name of the tool
        tool_use: Tool usage data
        tool_result: Tool execution result

    Returns:
        Formatted tool use string
    """
```

### Abstract Base Classes
```python
from abc import ABC, abstractmethod

class BaseFormatter(ABC):
    """Abstract base class for formatters."""

    @abstractmethod
    def format_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> str:
        """Format and return a conversation as a string."""
        pass
```

### Factory Pattern
```python
class FormatterFactory:
    @staticmethod
    def create_formatter(format_type: str, **kwargs) -> BaseFormatter:
        if format_type == OutputFormat.TERMINAL:
            return TerminalFormatter()
        elif format_type == OutputFormat.HTML:
            return HTMLFormatter()
        # ...
```

### Registry Pattern (for tool formatters)
```python
TOOL_FORMATTERS = {
    "Bash": BashFormatter(),
    "Read": ReadFormatter(),
    "Edit": EditFormatter(),
}

def format_tool_use(tool_name: str, tool_use: dict, tool_result: str | None = None) -> str:
    formatter = TOOL_FORMATTERS.get(tool_name)
    if formatter:
        return formatter.format(tool_use, tool_result)
    return f"[bold cyan]🔧 {tool_name}[/bold cyan]"
```

## Error Handling

### Try/Except with Specific Exceptions
```python
try:
    data = json.loads(line)
except json.JSONDecodeError as e:
    print(f"Warning: Failed to parse line: {e}")
```

### Early Returns for Validation
```python
def _display_message_group(self, messages: list[dict[str, Any]]) -> None:
    if not messages:
        return
    # ... rest of method
```

### Optional Dependencies
```python
def _check_dependencies(self) -> None:
    try:
        import asciinema  # noqa: F401
    except ImportError as err:
        raise ImportError(
            "asciinema is required. Install with: uv add --optional-deps animation"
        ) from err
```

## Rich Markup

Use Rich console markup for terminal output:
```python
# Colors and styles
"[bold red]Error:[/bold red]"
"[dim]({line_count} lines)[/dim]"
"[green]✓[/green]"

# Nested styles
"[bold cyan]Bash[/bold cyan]([yellow]{command}[/yellow])"
```

## HTML Generation

Build HTML as list of strings, then join:
```python
html_parts = []
html_parts.append('<div class="tool-use">')
html_parts.append(f'<strong>{html.escape(tool_name)}</strong>')
html_parts.append('</div>')
return "\n".join(html_parts)
```

Always escape user content:
```python
import html
html.escape(user_content)
```

## Testing Patterns

Currently no unit tests exist. When adding:
- Test files: `tests/test_*.py`
- Use pytest
- Mock external dependencies (file system, subprocess)

## Do's and Don'ts

### Do
- Use type hints everywhere
- Keep functions focused (single responsibility)
- Use early returns to reduce nesting
- Escape HTML content from user data
- Handle both string and dict formats for tool results
- Use Rich markup for terminal styling
- Group related functionality in classes

### Don't
- Use `# type: ignore` without explanation
- Catch bare `Exception` without re-raising
- Use mutable default arguments
- Mix tabs and spaces (use spaces only)
- Exceed 120 character line length
- Use star imports (`from x import *`)
- Commit commented-out code

## Ruff Configuration

From `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py311"
line-length = 120

[tool.ruff.lint]
select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "UP",  # pyupgrade
]
ignore = [
    "E501",  # line too long (handled by formatter)
    "B008",  # function calls in argument defaults
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

## Pre-commit Hooks

Automatically run on commit:
1. `ruff --fix` - Auto-fix linting issues
2. `ruff-format` - Format code
3. `check-added-large-files` - Prevent large file commits
4. `check-toml`, `check-yaml` - Validate config files
5. `end-of-file-fixer` - Ensure newline at EOF
6. `trailing-whitespace` - Remove trailing whitespace
