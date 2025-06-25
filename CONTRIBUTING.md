# Contributing to Claude Notes

Thank you for your interest in contributing to Claude Notes! This document provides guidelines for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Setup

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/yourusername/claude-notes.git
   cd claude-notes
   ```

3. Install dependencies:
   ```bash
   uv sync --all-extras
   ```

4. Verify the installation:
   ```bash
   uv run claude-notes --help
   ```

## Development Workflow

### Making Changes

1. Create a new branch for your feature/fix:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes in the `src/claude_notes/` directory

3. Test your changes:
   ```bash
   # Run the CLI to test functionality
   uv run claude-notes list-projects
   uv run claude-notes show --help
   
   # Test HTML output
   uv run claude-notes show --format html --output test.html
   ```

### Code Quality

Before submitting your changes, ensure they meet our quality standards:

```bash
# Format code
uv run ruff format

# Lint code
uv run ruff check

# Fix auto-fixable issues
uv run ruff check --fix
```

### Testing

While we don't have automated tests yet, please manually test:

1. **CLI Commands**: Ensure all commands work as expected
2. **Terminal Output**: Check that terminal formatting looks correct
3. **HTML Output**: Verify HTML export works and renders properly
4. **Edge Cases**: Test with empty conversations, missing files, etc.

## Code Structure

### Key Files

- `src/claude_notes/cli.py` - Command-line interface and main logic
- `src/claude_notes/parser.py` - JSONL transcript parsing
- `src/claude_notes/formatters/` - Output formatting modules
  - `base.py` - Base formatter class
  - `terminal.py` - Rich terminal formatting
  - `html.py` - HTML export with CSS
  - `factory.py` - Formatter creation
  - `tools.py` - Tool-specific formatters
- `src/claude_notes/pager.py` - Interactive paging for terminal

### Coding Guidelines

1. **Python Style**: Follow PEP 8, enforced by ruff
2. **Type Hints**: Use type hints for function parameters and return values
3. **Docstrings**: Add docstrings for classes and public methods
4. **Error Handling**: Handle errors gracefully with informative messages
5. **Rich Formatting**: Use Rich for terminal output, HTML for web output

### Adding New Features

#### New Output Formats

To add a new output format:

1. Create a new formatter class in `src/claude_notes/formatters/`
2. Inherit from `BaseFormatter` in `base.py`
3. Implement the `format_conversation` method
4. Add the formatter to `factory.py`
5. Update CLI to support the new format

#### New Tool Formatters

To add support for a new tool:

1. Add a formatter class to `html.py` (inherit from `HTMLToolFormatter`)
2. Add it to the `HTML_TOOL_FORMATTERS` registry
3. Add corresponding terminal formatter to `tools.py` if needed

## Submitting Changes

### Pull Request Process

1. Push your changes to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```

2. Create a pull request on GitHub with:
   - Clear title describing the change
   - Detailed description of what changed and why
   - Screenshots for UI changes
   - Link to any related issues

3. Ensure CI passes (GitHub Actions will run automatically)

4. Respond to code review feedback

### Commit Messages

Use clear, descriptive commit messages:

```
Add support for Glob tool in HTML formatter

- Create HTMLGlobFormatter class
- Add glob-specific styling
- Update tool registry
- Fix issue with pattern escaping
```

## Types of Contributions

### Bug Reports

When reporting bugs, please include:

- Operating system and Python version
- Steps to reproduce the issue
- Expected vs actual behavior
- Error messages or screenshots
- Sample JSONL files (if applicable and not sensitive)

### Feature Requests

For new features, please:

- Check existing issues to avoid duplicates
- Describe the use case and benefit
- Propose an implementation approach
- Consider backward compatibility

### Documentation

Documentation improvements are always welcome:

- Fix typos or unclear instructions
- Add examples or use cases
- Improve code comments
- Update README or other docs

## Getting Help

- **Questions**: Open a [GitHub Discussion](https://github.com/yourusername/claude-notes/discussions)
- **Bugs**: Create a [GitHub Issue](https://github.com/yourusername/claude-notes/issues)
- **Chat**: Join discussions in existing issues

## Code of Conduct

Please be respectful and constructive in all interactions. We aim to create a welcoming environment for all contributors.

Thank you for contributing to Claude Notes! 🎉