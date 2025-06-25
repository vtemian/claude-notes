# Claude Notes

Transform Claude Code transcript JSONL files into readable terminal and HTML formats.

## Overview

Claude Notes is a command-line tool that converts Claude Code conversation transcripts (stored as JSONL files) into human-readable formats. It supports both terminal output with rich formatting and HTML export for web viewing.

```bash
uvx claude-notes show --format html --output conversations.html
```

## Features

- Terminal display with syntax highlighting and rich formatting
- HTML export with navigation, timestamps, and professional styling
- Interactive pager for browsing long conversations
- Project discovery - automatically finds Claude projects
- Humanized timestamps - shows "2 hours ago" instead of raw timestamps
- Tool result formatting - properly displays Bash, Read, Edit, MultiEdit, and Grep tool usage
- Navigation links - jump to specific messages in HTML output

## Usage

#### HTML Output

```bash
# Export to HTML file
uvx claude-notes show --format html --output conversations.html

# Print HTML to stdout
uvx claude-notes show --format html
```

#### Terminal Output

```bash
# View conversations for current directory
uvx claude-notes show

# View conversations for specific project path
uvx claude-notes show /path/to/project

# Disable pager (show all at once)
uvx claude-notes show --no-pager

# Show raw JSON data
uvx claude-notes show --raw
```

### Examples

```bash
# View current project conversations in terminal
claude-notes show

# Export project conversations to HTML
claude-notes show /Users/john/myproject --format html --output myproject-conversations.html

# Browse all conversations with interactive pager
claude-notes show --no-pager=false

# See all available Claude projects
claude-notes list-projects
```

## HTML Features

The HTML output includes:

- **Message Navigation**: Each message has a clickable heading with anchor links
- **Humanized Timestamps**: Shows when each message was created (e.g., "2 hours ago")
- **Tool Result Formatting**: 
  - Bash commands with syntax highlighting
  - File operations (Read, Edit, MultiEdit)
  - Search results (Grep)
- **Responsive Design**: Works well on desktop and mobile
- **Professional Styling**: Clean, readable typography

## How It Works

Claude Code stores conversation transcripts as JSONL files in `~/.claude/projects/`. Each line represents a message, tool use, or tool result. Claude Notes:

1. Discovers Claude projects by scanning the projects directory
2. Parses JSONL transcript files 
3. Groups related messages by role continuity
4. Formats tool usage and results appropriately
5. Outputs in your chosen format (terminal or HTML)

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Test thoroughly
5. Submit a pull request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

- Report issues: [GitHub Issues](https://github.com/yourusername/claude-notes/issues)
- Feature requests: [GitHub Discussions](https://github.com/yourusername/claude-notes/discussions)
