# Claude Notes

Transform Claude Code transcript JSONL files into readable terminal and HTML formats.

## Overview

Claude Notes is a command-line tool that converts Claude Code conversation transcripts (stored as JSONL files) into human-readable formats. It supports both terminal output with rich formatting and HTML export for web viewing.

```bash
uvx claude-notes show --format html --output conversations.html
```


https://github.com/user-attachments/assets/f24d143d-cb47-495a-b1f8-3e85863e5846


```bash
uvx claude-notes show
```

https://github.com/user-attachments/assets/ca710fb3-558a-4ce5-9bf5-e42c80caf2bf


## Examples

See rendered HTML output examples:

- [Conversation Export](https://htmlpreview.github.io/?https://github.com/vtemian/claude-notes/blob/main/examples/conversations.html) - Full conversation with tool usage, code blocks, and timestamps

The `examples/` directory also contains a [dark theme CSS](examples/example-dark-style.css) you can use to customize the HTML output.

<img width="1326" height="1299" alt="Screenshot 2026-01-13 at 6 35 29 PM" src="https://github.com/user-attachments/assets/a85132ad-b727-466f-b0d7-cff3a85be486" />

## Features

- Terminal display with syntax highlighting and rich formatting
- HTML export with navigation, timestamps, and professional styling
- Interactive pager for browsing long conversations
- Project discovery - automatically finds Claude projects
- Humanized timestamps - shows "2 hours ago" instead of raw timestamps
- Tool result formatting - properly displays Bash, Read, Edit, MultiEdit, and Grep tool usage
- Navigation links - jump to specific messages in HTML output

## Acknowledge

This tool was heavily inspired by https://github.com/daaain/claude-code-log

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

- Report issues: [GitHub Issues](https://github.com/vtemian/claude-notes/issues)
- Feature requests: [GitHub Discussions](https://github.com/vtemian/claude-notes/discussions)
