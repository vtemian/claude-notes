"""HTML formatter for Claude conversations."""

import html
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_notes.formatters.base import BaseFormatter


def humanize_date(timestamp_str: str) -> str:
    """Convert ISO timestamp to humanized format."""
    try:
        # Parse the ISO timestamp
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(UTC)

        # Calculate time difference
        diff = now - dt

        # Convert to local time for display
        local_dt = dt.astimezone()

        # Format based on time difference
        total_seconds = diff.total_seconds()

        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:  # Less than 1 hour
            minutes = int(total_seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        elif total_seconds < 86400:  # Less than 1 day
            hours = int(total_seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif total_seconds < 2592000:  # Less than 30 days
            days = int(total_seconds / 86400)
            return f"{days} day{'s' if days != 1 else ''} ago"
        else:
            # For older dates, show the actual date
            return local_dt.strftime("%B %d, %Y at %I:%M %p")
    except (ValueError, TypeError):
        # Fallback for unparseable dates
        return timestamp_str


class HTMLFormatter(BaseFormatter):
    """Format Claude conversations for HTML display."""

    def __init__(self):
        """Initialize the formatter."""
        super().__init__()

    def format_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> str:
        """Format and return a conversation as HTML."""
        # Collect tool results
        self._collect_tool_results(messages)

        # Group messages by role continuity
        grouped_messages = self._group_messages(messages)

        # Build HTML
        html_parts = []
        html_parts.append('<div class="conversation">')

        # Add conversation header if available
        conversation_id = conversation_info.get("conversation_id", "unknown")
        if conversation_id:
            html_parts.append('<div class="conversation-header">')
            html_parts.append(f'<h2 id="conv-{conversation_id}">Conversation {conversation_id}</h2>')
            if conversation_info.get("start_time"):
                html_parts.append(f'<div class="timestamp">{conversation_info["start_time"]}</div>')
            html_parts.append("</div>")

        # Display each group with headings and anchors
        for i, group in enumerate(grouped_messages):
            html_parts.append(self._format_message_group(group, i + 1))

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _format_message_group(self, messages: list[dict[str, Any]], message_number: int = None) -> str:
        """Format a group of messages from the same role."""
        if not messages:
            return ""

        # Get the role from the first message
        first_msg = messages[0]
        message_data = first_msg.get("message", {})
        role = message_data.get("role", "unknown")

        # Process each message separately but display as one group
        message_parts = []

        for msg in messages:
            msg_content = []

            # Handle tool results that are stored at the message level
            if msg.get("type") == "tool_result":
                continue

            message_data = msg.get("message", {})
            content = message_data.get("content", "")

            if isinstance(content, str):
                msg_content.append(self._format_text_content(content, role))
            elif isinstance(content, list):
                # Handle content array (e.g., text + tool uses)
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            msg_content.append(self._format_text_content(item.get("text", ""), role))
                        elif item.get("type") == "tool_use":
                            msg_content.append(self._format_tool_use_html(item, msg))

            # Join content for this message
            if msg_content:
                message_parts.append("".join(msg_content))

        if not message_parts:
            return ""

        # Create message group HTML with heading and anchor
        role_class = f"message-group {role}"
        role_icon = "👤" if role == "user" else "🤖" if role == "assistant" else "⚙️"
        role_name = role.title()

        html_parts = []

        html_parts.append(f'<div class="{role_class}">')

        # Add message header with role, anchor, and timestamp
        header_parts = []
        header_parts.append('<div class="message-header">')
        header_parts.append(f'<h3 id="msg-{message_number}" class="message-title">')
        header_parts.append(f"{role_icon} {role_name}")
        header_parts.append(f'<a href="#msg-{message_number}" class="anchor-link">#</a>')
        header_parts.append("</h3>")

        # Add timestamp if available (use first message's timestamp for the group)
        if messages and messages[0].get("timestamp"):
            timestamp_str = messages[0]["timestamp"]
            humanized = humanize_date(timestamp_str)
            header_parts.append(f'<div class="message-timestamp">{humanized}</div>')

        header_parts.append("</div>")
        html_parts.extend(header_parts)

        # Add message content
        html_parts.append('<div class="message-content">')
        for part in message_parts:
            html_parts.append(part)
        html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)

    def _get_message_preview(self, messages: list[dict[str, Any]], max_length: int = 50) -> str:
        """Generate a preview of the message content for navigation."""
        if not messages:
            return "Empty message"

        # Extract text content from the first message
        first_msg = messages[0]
        message_data = first_msg.get("message", {})
        content = message_data.get("content", "")

        preview_text = ""

        if isinstance(content, str):
            preview_text = content.strip()
        elif isinstance(content, list):
            # Look for text content in the list
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text = item.get("text", "").strip()
                    if text:
                        preview_text = text
                        break
                elif isinstance(item, dict) and item.get("type") == "tool_use":
                    tool_name = item.get("name", "Unknown Tool")
                    preview_text = f"[{tool_name} tool usage]"
                    break

        # Clean up the preview text
        if preview_text:
            # Remove markdown formatting for preview
            preview_text = re.sub(r"\*\*(.*?)\*\*", r"\1", preview_text)  # Remove bold
            preview_text = re.sub(r"\*(.*?)\*", r"\1", preview_text)  # Remove italic
            preview_text = re.sub(r"`(.*?)`", r"\1", preview_text)  # Remove code
            preview_text = re.sub(r"#+\s*", "", preview_text)  # Remove headers

            # Don't truncate for HTML - show full preview
            return html.escape(preview_text)

        return "No content"

    def _format_text_content(self, content: str, role: str) -> str:
        """Format text content with proper HTML escaping and markdown conversion."""
        if not content.strip():
            return ""

        # Escape HTML
        content = html.escape(content)

        # Convert markdown to HTML
        content = self._markdown_to_html(content)

        # Handle special tags for user messages
        if role == "user":
            content = self._parse_special_tags_html(content)

        return f'<div class="text-content">{content}</div>'

    def _markdown_to_html(self, content: str) -> str:
        """Convert basic markdown to HTML."""
        # Bold **text**
        content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)

        # Italic *text*
        content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)

        # Code `code`
        content = re.sub(r"`(.*?)`", r"<code>\1</code>", content)

        # Headers
        content = re.sub(r"^### (.*?)$", r"<h3>\1</h3>", content, flags=re.MULTILINE)
        content = re.sub(r"^## (.*?)$", r"<h2>\1</h2>", content, flags=re.MULTILINE)
        content = re.sub(r"^# (.*?)$", r"<h1>\1</h1>", content, flags=re.MULTILINE)

        # Line breaks
        content = content.replace("\n", "<br>\n")

        return content

    def _parse_special_tags_html(self, content: str) -> str:
        """Parse special tags in content for HTML."""
        # Replace command-message tags
        content = re.sub(
            r"<command-message>(.*?)</command-message>",
            r'<span class="command-message">\1</span>',
            content,
            flags=re.DOTALL,
        )

        # Replace command-name tags
        content = re.sub(
            r"<command-name>(.*?)</command-name>", r'<span class="command-name">\1</span>', content, flags=re.DOTALL
        )

        # Replace system-reminder tags
        content = re.sub(
            r"<system-reminder>(.*?)</system-reminder>",
            r'<div class="system-reminder">System: \1</div>',
            content,
            flags=re.DOTALL,
        )

        return content

    def _format_tool_use_html(self, tool_use: dict[str, Any], msg: dict[str, Any]) -> str:
        """Format a tool use block with its result for HTML."""
        tool_name = tool_use.get("name", "Unknown Tool")
        tool_id = tool_use.get("id")

        # Find the tool result for this tool use
        tool_result = None
        if tool_id:
            # First check if there's a result mapped by the message UUID
            msg_uuid = msg.get("uuid")
            if msg_uuid and msg_uuid in self._tool_results:
                tool_result = self._tool_results[msg_uuid]
            # Also check by tool use ID (some formats might use this)
            elif tool_id in self._tool_results:
                tool_result = self._tool_results[tool_id]

        # Use the specific formatter for this tool
        return self.format_tool_use(tool_name, tool_use, tool_result)

    def format_tool_use(self, tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use with the appropriate HTML formatter."""
        formatter = HTML_TOOL_FORMATTERS.get(tool_name)

        if formatter:
            return formatter.format(tool_use, tool_result)
        else:
            # Fallback for unknown tools
            return f'<div class="tool-use unknown-tool"><span class="tool-icon">🔧</span> <strong>{html.escape(tool_name)}</strong></div>'


class HTMLToolFormatter:
    """Base class for HTML tool formatters."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use and its result as HTML."""
        raise NotImplementedError


class HTMLBashFormatter(HTMLToolFormatter):
    """Format Bash tool usage for HTML."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format Bash command and output."""
        input_data = tool_use.get("input", {})
        command = input_data.get("command", "unknown command")

        # Don't truncate commands for HTML
        display_command = command

        # Format the command line
        html_parts = []
        html_parts.append('<div class="tool-use bash-tool">')
        html_parts.append('<div class="tool-header">')
        html_parts.append('<span class="tool-icon">⏺</span>')
        html_parts.append(f"<strong>Bash</strong>(<code>{html.escape(display_command)}</code>)")
        html_parts.append("</div>")

        # Handle both string and dict formats for tool_result
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and str(result_text).strip():
            lines = str(result_text).strip().split("\n")
            # Filter out empty lines
            lines = [line for line in lines if line.strip()]

            if lines:
                html_parts.append('<div class="tool-output">')
                # Show all lines without truncation
                for line in lines:
                    html_parts.append(f'<div class="output-line">{html.escape(line)}</div>')
                html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)


class HTMLReadFormatter(HTMLToolFormatter):
    """Format Read tool usage for HTML."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format file read operation."""
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")

        # Extract just the filename
        filename = Path(file_path).name

        html_parts = []
        html_parts.append('<div class="tool-use read-tool">')
        html_parts.append('<div class="tool-header">')
        html_parts.append('<span class="tool-icon">📄</span>')
        html_parts.append(f"<strong>Read</strong>(<code>{html.escape(filename)}</code>)")
        html_parts.append("</div>")

        if tool_result:
            # Handle both string and dict formats for tool_result
            result_text = tool_result
            if isinstance(tool_result, dict) and "text" in tool_result:
                result_text = tool_result["text"]

            lines = str(result_text).strip().split("\n")
            line_count = len(lines)

            html_parts.append(f'<div class="file-info">({line_count} lines)</div>')

            # Show full file content without truncation
            html_parts.append('<div class="file-preview">')
            for line in lines:
                html_parts.append(f'<div class="file-line">{html.escape(line)}</div>')
            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)


class HTMLEditFormatter(HTMLToolFormatter):
    """Format Edit tool usage for HTML."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format file edit operation."""
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        old_string = input_data.get("old_string", "")
        new_string = input_data.get("new_string", "")

        filename = Path(file_path).name

        # Count changed lines
        old_lines = old_string.split("\n") if old_string else []
        new_lines = new_string.split("\n") if new_string else []

        html_parts = []
        html_parts.append('<div class="tool-use edit-tool">')
        html_parts.append('<div class="tool-header">')
        html_parts.append('<span class="tool-icon">✏️</span>')
        html_parts.append(f"<strong>Edit</strong>(<code>{html.escape(filename)}</code>)")

        # Show line count change
        if len(old_lines) == len(new_lines):
            html_parts.append(f'<span class="edit-info">({len(old_lines)} lines modified)</span>')
        else:
            diff = len(new_lines) - len(old_lines)
            if diff > 0:
                html_parts.append(f'<span class="edit-info">(+{diff} lines)</span>')
            else:
                html_parts.append(f'<span class="edit-info">({diff} lines)</span>')

        # Handle success check for both formats
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and "updated" in str(result_text).lower():
            html_parts.append('<span class="success-indicator">✓</span>')

        html_parts.append("</div>")

        # Show diff preview
        if old_lines or new_lines:
            html_parts.append('<div class="diff-preview">')
            # Show all removed lines
            for line in old_lines:
                if line.strip():
                    html_parts.append(f'<div class="diff-line removed">- {html.escape(line)}</div>')

            # Show all added lines
            for line in new_lines:
                if line.strip():
                    html_parts.append(f'<div class="diff-line added">+ {html.escape(line)}</div>')

            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)


class HTMLMultiEditFormatter(HTMLToolFormatter):
    """Format MultiEdit tool usage for HTML."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format multi-edit operation."""
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        edits = input_data.get("edits", [])

        filename = Path(file_path).name

        html_parts = []
        html_parts.append('<div class="tool-use multiedit-tool">')
        html_parts.append('<div class="tool-header">')
        html_parts.append('<span class="tool-icon">✏️</span>')
        html_parts.append(f"<strong>MultiEdit</strong>(<code>{html.escape(filename)}</code>)")

        # Show edit count
        edit_count = len(edits)
        html_parts.append(f'<span class="edit-info">({edit_count} edits)</span>')

        # Handle success check for both formats
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and ("updated" in str(result_text).lower() or "applied" in str(result_text).lower()):
            html_parts.append('<span class="success-indicator">✓</span>')

        html_parts.append("</div>")

        # Show each edit as a diff
        if edits:
            html_parts.append('<div class="multiedit-preview">')
            for i, edit in enumerate(edits, 1):
                old_string = edit.get("old_string", "")
                new_string = edit.get("new_string", "")
                replace_all = edit.get("replace_all", False)

                html_parts.append('<div class="edit-section">')
                html_parts.append(
                    f'<div class="edit-number">Edit {i}' + (" (replace all)" if replace_all else "") + "</div>"
                )

                # Show diff for this edit
                old_lines = old_string.split("\n") if old_string else []
                new_lines = new_string.split("\n") if new_string else []

                html_parts.append('<div class="diff-preview">')

                # Show all removed lines
                for line in old_lines:
                    if line.strip() or old_lines == [""]:  # Show empty lines too if that's the only content
                        html_parts.append(f'<div class="diff-line removed">- {html.escape(line)}</div>')

                # Show all added lines
                for line in new_lines:
                    if line.strip() or new_lines == [""]:  # Show empty lines too if that's the only content
                        html_parts.append(f'<div class="diff-line added">+ {html.escape(line)}</div>')

                html_parts.append("</div>")
                html_parts.append("</div>")

            html_parts.append("</div>")

        html_parts.append("</div>")
        return "\n".join(html_parts)


class HTMLGrepFormatter(HTMLToolFormatter):
    """Format Grep tool usage for HTML."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format grep search operation."""
        input_data = tool_use.get("input", {})
        pattern = input_data.get("pattern", "unknown pattern")
        path = input_data.get("path", ".")
        include = input_data.get("include", "")

        html_parts = []
        html_parts.append('<div class="tool-use grep-tool">')
        html_parts.append('<div class="tool-header">')
        html_parts.append('<span class="tool-icon">🔍</span>')
        html_parts.append(f"<strong>Grep</strong>(<code>{html.escape(pattern)}</code>")

        # Add path and include info if different from defaults
        if path != ".":
            html_parts.append(f" in <code>{html.escape(path)}</code>")
        if include:
            html_parts.append(f" include <code>{html.escape(include)}</code>")

        html_parts.append(")")
        html_parts.append("</div>")

        # Handle both string and dict formats for tool_result
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and str(result_text).strip():
            lines = str(result_text).strip().split("\n")
            # Filter out empty lines
            lines = [line for line in lines if line.strip()]

            if lines:
                # Count matches
                file_count = len(lines)
                html_parts.append(f'<div class="grep-info">Found {file_count} matching files</div>')

                html_parts.append('<div class="tool-output">')
                # Show all matching files
                for line in lines:
                    html_parts.append(f'<div class="output-line">{html.escape(line)}</div>')
                html_parts.append("</div>")
        else:
            html_parts.append('<div class="grep-info">No matches found</div>')

        html_parts.append("</div>")
        return "\n".join(html_parts)


# Registry of HTML tool formatters
HTML_TOOL_FORMATTERS = {
    "Bash": HTMLBashFormatter(),
    "Read": HTMLReadFormatter(),
    "Edit": HTMLEditFormatter(),
    "MultiEdit": HTMLMultiEditFormatter(),
    "Grep": HTMLGrepFormatter(),
    # Add more formatters as needed
}


def get_extra_html_css(css_file_path: str | None = None) -> str:
    """Return extra CSS styles from a custom stylesheet file."""
    if not css_file_path:
        return ""

    try:
        css_path = Path(css_file_path)
        if css_path.exists():
            return f"\n<style>\n{css_path.read_text(encoding='utf-8')}\n</style>"
    except Exception:
        # Silently ignore errors reading the CSS file
        pass

    return ""


def get_html_css() -> str:
    """Return CSS styles for HTML output - nof1-inspired terminal aesthetic."""
    return """
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@100;200;300;400;500;600;700&display=swap");

:root {
    --background: #ffffff;
    --surface: #ffffff;
    --surface-elevated: #f8f9fa;
    --foreground: #000000;
    --foreground-muted: #333333;
    --foreground-subtle: #666666;
    --border: #000000;
    --border-subtle: #cccccc;
    --terminal-green: #00aa00;
    --terminal-red: #cc0000;
    --terminal-yellow: #b8860b;
    --terminal-blue: #0000aa;
}

[data-theme="dark"] {
    --background: #000000;
    --surface: #0a0a0a;
    --surface-elevated: #111111;
    --foreground: #00ff00;
    --foreground-muted: #00cc00;
    --foreground-subtle: #00aa00;
    --border: #00ff00;
    --border-subtle: #006600;
    --terminal-green: #00ff00;
    --terminal-red: #ff0000;
    --terminal-yellow: #ffff00;
    --terminal-blue: #00ffff;
}

*, *:before, *:after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html, body {
    height: 100%;
    background: var(--background);
    color: var(--foreground);
    font-family: "IBM Plex Mono", monospace;
    font-feature-settings: "cv02", "cv03", "cv04", "cv11";
    line-height: 1.5;
    letter-spacing: -0.02em;
}

/* Noise texture overlay */
body::before {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.6' numOctaves='4' stitchTiles='stitch'/%3E%3CfeColorMatrix type='saturate' values='0'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)' opacity='0.15'/%3E%3C/svg%3E");
    background-size: 180px 180px;
    pointer-events: none;
    z-index: 1;
    opacity: 0.5;
}

.conversation {
    position: relative;
    z-index: 2;
    max-width: 900px;
    margin: 0 auto;
    padding: 40px 20px;
}

/* Headers - uppercase terminal style */
h1, h2, h3, h4, h5, h6 {
    font-family: "IBM Plex Mono", monospace;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    line-height: 1.2;
}

.conversation-header {
    margin-bottom: 40px;
    padding-bottom: 20px;
    border-bottom: 2px solid var(--border);
}

.conversation-header h2 {
    margin: 0;
    color: var(--foreground);
    font-size: 1.1rem;
}

.timestamp {
    color: var(--foreground-subtle);
    font-size: 0.75rem;
    margin-top: 8px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Navigation */
.message-nav, .conversation-nav {
    background-color: var(--surface);
    border: 1px solid var(--border);
    padding: 20px;
    margin-bottom: 30px;
}

.message-nav h3, .conversation-nav h2 {
    margin: 0 0 15px 0;
    color: var(--foreground);
    font-size: 0.875rem;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 10px;
}

.message-toc, .conversation-toc {
    list-style: none;
    padding: 0;
    margin: 0;
}

.message-toc li, .conversation-toc li {
    margin-bottom: 4px;
}

.message-toc a, .conversation-toc a {
    color: var(--foreground);
    text-decoration: none;
    padding: 6px 10px;
    display: block;
    font-size: 0.8rem;
    border: 1px solid transparent;
    transition: none;
}

.message-toc a:hover, .conversation-toc a:hover {
    background-color: var(--foreground);
    color: var(--background);
    text-decoration: none;
}

/* Message sections */
.message-header {
    margin: 50px 0 15px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}

.message-title {
    margin: 0;
    color: var(--foreground);
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    gap: 8px;
}

.anchor-link {
    color: var(--foreground-subtle);
    text-decoration: none;
    font-weight: normal;
    font-size: 0.75rem;
}

.anchor-link:hover {
    color: var(--foreground);
}

.message-timestamp {
    color: var(--foreground-subtle);
    font-size: 0.7rem;
    font-weight: normal;
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.message-group {
    margin-bottom: 30px;
}

.message-group.user {
    border-left: 3px solid var(--foreground);
    padding-left: 15px;
}

.message-group.assistant {
    border-left: 3px solid var(--foreground-subtle);
    padding-left: 15px;
}

.message-content {
    flex: 1;
    min-width: 0;
}

/* Back to top */
.back-to-top {
    text-align: center;
    margin: 50px 0 20px 0;
    padding-top: 20px;
    border-top: 1px solid var(--border);
}

.back-to-top a {
    color: var(--foreground);
    text-decoration: none;
    padding: 8px 16px;
    background-color: var(--surface);
    border: 1px solid var(--border);
    display: inline-block;
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    transition: none;
}

.back-to-top a:hover {
    background-color: var(--foreground);
    color: var(--background);
}

/* Text content */
.text-content {
    margin-bottom: 15px;
    font-size: 0.875rem;
    line-height: 1.6;
}

.text-content h1, .text-content h2, .text-content h3 {
    margin: 25px 0 12px 0;
    color: var(--foreground);
}

.text-content h1 { font-size: 1rem; }
.text-content h2 { font-size: 0.9rem; }
.text-content h3 { font-size: 0.85rem; }

.text-content code {
    background-color: var(--surface-elevated);
    padding: 2px 6px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.85em;
    border: 1px solid var(--border-subtle);
}

.text-content strong {
    font-weight: 600;
}

/* Tool blocks - terminal style */
.tool-use {
    background-color: var(--surface);
    border: 1px solid var(--border);
    padding: 12px 15px;
    margin: 15px 0;
    font-size: 0.8rem;
}

.tool-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
    font-size: 0.8rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.tool-icon {
    font-size: 1em;
}

.bash-tool .tool-header {
    color: var(--terminal-red);
}

.read-tool .tool-header {
    color: var(--terminal-green);
}

.edit-tool .tool-header,
.multiedit-tool .tool-header {
    color: var(--terminal-yellow);
}

.grep-tool .tool-header {
    color: var(--terminal-blue);
}

.tool-output, .file-preview, .diff-preview, .multiedit-preview {
    background-color: var(--surface-elevated);
    border: 1px solid var(--border-subtle);
    padding: 10px 12px;
    margin-top: 10px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.75rem;
    overflow-x: auto;
}

.output-line, .file-line {
    margin-bottom: 1px;
    white-space: pre-wrap;
    word-break: break-all;
}

.output-summary {
    color: var(--foreground-subtle);
    font-style: italic;
    margin-top: 8px;
    font-size: 0.7rem;
}

.file-info, .edit-info, .grep-info {
    color: var(--foreground-subtle);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

.edit-info, .grep-info {
    margin-left: 10px;
}

.success-indicator {
    color: var(--terminal-green);
    margin-left: 8px;
}

/* Diff styling */
.diff-line {
    margin-bottom: 1px;
    padding: 1px 4px;
    font-family: "IBM Plex Mono", monospace;
}

.diff-line.removed {
    background-color: rgba(204, 0, 0, 0.15);
    color: var(--terminal-red);
}

.diff-line.added {
    background-color: rgba(0, 170, 0, 0.15);
    color: var(--terminal-green);
}

[data-theme="dark"] .diff-line.removed {
    background-color: rgba(255, 0, 0, 0.2);
}

[data-theme="dark"] .diff-line.added {
    background-color: rgba(0, 255, 0, 0.15);
}

/* Special tags */
.command-message {
    font-style: italic;
    color: var(--foreground-subtle);
}

.command-name {
    font-weight: 600;
    color: var(--terminal-blue);
}

.system-reminder {
    background-color: rgba(184, 134, 11, 0.1);
    border: 1px solid var(--terminal-yellow);
    border-left: 3px solid var(--terminal-yellow);
    padding: 10px 12px;
    margin: 12px 0;
    color: var(--foreground);
    font-size: 0.75rem;
}

.unknown-tool {
    border-left: 3px solid var(--foreground-subtle);
}

/* Multi-edit sections */
.edit-section {
    margin-bottom: 15px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-subtle);
}

.edit-section:last-child {
    border-bottom: none;
    margin-bottom: 0;
    padding-bottom: 0;
}

.edit-number {
    font-weight: 600;
    color: var(--foreground);
    margin-bottom: 6px;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}

/* Theme toggle button (optional) */
.theme-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 100;
    background: var(--surface);
    border: 1px solid var(--border);
    color: var(--foreground);
    padding: 6px 12px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    cursor: pointer;
}

.theme-toggle:hover {
    background: var(--foreground);
    color: var(--background);
}

/* Scrollbar hiding */
* {
    scrollbar-width: none !important;
    -ms-overflow-style: none !important;
}

*::-webkit-scrollbar {
    display: none !important;
}

/* Print styles */
@media print {
    body::before {
        display: none;
    }
    .theme-toggle {
        display: none;
    }
    .conversation {
        max-width: 100%;
        padding: 0;
    }
}
</style>
"""
