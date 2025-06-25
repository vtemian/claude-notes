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


def get_html_css() -> str:
    """Return CSS styles for HTML output."""
    return """
<style>
.conversation {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
    line-height: 1.6;
}

.conversation-header {
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 2px solid #e1e5e9;
}

.conversation-header h2 {
    margin: 0;
    color: #2c3e50;
}

.timestamp {
    color: #6c757d;
    font-size: 0.9em;
    margin-top: 5px;
}

.message-nav {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.message-nav h3 {
    margin: 0 0 15px 0;
    color: #2c3e50;
    font-size: 1.1em;
}

.message-toc {
    list-style: none;
    padding: 0;
    margin: 0;
}

.message-toc li {
    margin-bottom: 8px;
}

.message-toc a {
    color: #007bff;
    text-decoration: none;
    padding: 8px 12px;
    border-radius: 4px;
    display: block;
    transition: background-color 0.2s;
}

.message-toc a:hover {
    background-color: #e9ecef;
    text-decoration: none;
}

.message-header {
    margin: 40px 0 20px 0;
    padding-bottom: 10px;
    border-bottom: 1px solid #e1e5e9;
}

.message-title {
    margin: 0;
    color: #2c3e50;
    font-size: 1.3em;
    display: flex;
    align-items: center;
    gap: 10px;
}

.anchor-link {
    color: #6c757d;
    text-decoration: none;
    font-weight: normal;
    transition: opacity 0.2s;
}

.anchor-link:hover {
    color: #007bff;
}

.message-timestamp {
    color: #6c757d;
    font-size: 0.8em;
    font-weight: normal;
    margin-top: 2px;
}

.message-group {
    margin-bottom: 25px;
    display: flex;
    gap: 15px;
}

.message-group.user {
    flex-direction: row;
}

.message-group.assistant {
    flex-direction: row;
}

.role-indicator {
    flex-shrink: 0;
    font-size: 1.2em;
    margin-top: 5px;
}

.message-content {
    flex: 1;
    min-width: 0;
}

.conversation-nav {
    background-color: #f1f3f4;
    border: 1px solid #dadce0;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 30px;
}

.conversation-nav h2 {
    margin: 0 0 15px 0;
    color: #2c3e50;
    font-size: 1.2em;
}

.conversation-toc {
    list-style: none;
    padding: 0;
    margin: 0;
}

.conversation-toc li {
    margin-bottom: 10px;
}

.conversation-toc a {
    color: #1a73e8;
    text-decoration: none;
    padding: 10px 15px;
    border-radius: 6px;
    display: block;
    background-color: white;
    border: 1px solid #dadce0;
    transition: all 0.2s;
}

.conversation-toc a:hover {
    background-color: #f8f9fa;
    border-color: #1a73e8;
    text-decoration: none;
}

.back-to-top {
    text-align: center;
    margin: 40px 0 20px 0;
    padding-top: 20px;
    border-top: 1px solid #e1e5e9;
}

.back-to-top a {
    color: #6c757d;
    text-decoration: none;
    padding: 10px 20px;
    border-radius: 20px;
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    transition: all 0.2s;
    display: inline-block;
}

.back-to-top a:hover {
    color: #007bff;
    background-color: #e9ecef;
    text-decoration: none;
}

.text-content {
    margin-bottom: 15px;
}

.text-content h1, .text-content h2, .text-content h3 {
    margin: 20px 0 10px 0;
    color: #2c3e50;
}

.text-content code {
    background-color: #f8f9fa;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
}

.text-content strong {
    font-weight: 600;
}

.tool-use {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 15px;
    margin: 15px 0;
}

.tool-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
    font-size: 1.1em;
}

.tool-icon {
    font-size: 1.2em;
}

.bash-tool .tool-header {
    color: #dc3545;
}

.read-tool .tool-header {
    color: #28a745;
}

.edit-tool .tool-header {
    color: #ffc107;
}

.multiedit-tool .tool-header {
    color: #ffc107;
}

.grep-tool .tool-header {
    color: #17a2b8;
}

.tool-output, .file-preview, .diff-preview {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 10px;
    margin-top: 10px;
    font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
    font-size: 0.9em;
}

.output-line, .file-line {
    margin-bottom: 2px;
}

.output-summary {
    color: #6c757d;
    font-style: italic;
    margin-top: 5px;
}

.file-info {
    color: #6c757d;
    font-size: 0.9em;
}

.edit-info {
    color: #6c757d;
    font-size: 0.9em;
    margin-left: 10px;
}

.success-indicator {
    color: #28a745;
    margin-left: 10px;
}

.diff-line {
    margin-bottom: 2px;
    padding: 2px 0;
}

.diff-line.removed {
    background-color: #ffe6e6;
    color: #d73a49;
}

.diff-line.added {
    background-color: #e6ffed;
    color: #28a745;
}

.command-message {
    font-style: italic;
    color: #6c757d;
}

.command-name {
    font-weight: 600;
    color: #007bff;
}

.system-reminder {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 4px;
    padding: 10px;
    margin: 10px 0;
    color: #856404;
}

.unknown-tool {
    border-left: 4px solid #6c757d;
}

.multiedit-preview {
    background-color: #ffffff;
    border: 1px solid #dee2e6;
    border-radius: 4px;
    padding: 10px;
    margin-top: 10px;
}

.edit-section {
    margin-bottom: 15px;
    padding-bottom: 10px;
    border-bottom: 1px solid #e9ecef;
}

.edit-section:last-child {
    border-bottom: none;
    margin-bottom: 0;
}

.edit-number {
    font-weight: 600;
    color: #495057;
    margin-bottom: 5px;
    font-size: 0.9em;
}

.grep-info {
    color: #6c757d;
    font-size: 0.9em;
    margin-bottom: 10px;
}
</style>
"""
