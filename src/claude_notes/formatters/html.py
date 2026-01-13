"""HTML formatter for Claude conversations - ampcode-inspired design."""

import html
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from claude_notes.formatters.base import BaseFormatter


def humanize_date(timestamp_str: str) -> str:
    """Convert ISO timestamp to humanized format."""
    try:
        dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        now = datetime.now(UTC)
        diff = now - dt
        total_seconds = diff.total_seconds()

        if total_seconds < 60:
            return "just now"
        elif total_seconds < 3600:
            minutes = int(total_seconds / 60)
            return f"{minutes}m ago"
        elif total_seconds < 86400:
            hours = int(total_seconds / 3600)
            return f"{hours}h ago"
        elif total_seconds < 2592000:
            days = int(total_seconds / 86400)
            return f"{days}d ago"
        else:
            local_dt = dt.astimezone()
            return local_dt.strftime("%b %d, %Y")
    except (ValueError, TypeError):
        return timestamp_str


class HTMLFormatter(BaseFormatter):
    """Format Claude conversations for HTML display - ampcode style."""

    def __init__(self):
        """Initialize the formatter."""
        super().__init__()
        self.stats = {
            "files_read": set(),
            "files_edited": set(),
            "lines_added": 0,
            "lines_removed": 0,
            "tool_calls": 0,
            "searches": 0,
            "bash_commands": 0,
        }

    def format_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> str:
        """Format and return a conversation as HTML."""
        # Reset stats for this conversation
        self.stats = {
            "files_read": set(),
            "files_edited": set(),
            "lines_added": 0,
            "lines_removed": 0,
            "tool_calls": 0,
            "searches": 0,
            "bash_commands": 0,
        }

        # Collect tool results
        self._collect_tool_results(messages)

        # Group messages by role continuity
        grouped_messages = self._group_messages(messages)

        # Extract title from first user message
        title = self._extract_title(grouped_messages)

        # Build HTML
        html_parts = []
        conversation_id = conversation_info.get("conversation_id", "unknown")

        html_parts.append(f'<article class="thread" id="conv-{conversation_id}">')

        # Thread header
        html_parts.append('<header class="thread-header">')
        html_parts.append(f'<h1 class="thread-title">{html.escape(title)}</h1>')
        html_parts.append('<div class="thread-meta">')
        if conversation_info.get("start_time"):
            humanized = humanize_date(conversation_info["start_time"])
            html_parts.append(f'<span class="meta-item">{humanized}</span>')
        message_count = len(grouped_messages)
        html_parts.append(f'<span class="meta-item">{message_count} messages</span>')
        html_parts.append("</div>")
        html_parts.append("</header>")

        # Main content area
        html_parts.append('<div class="thread-body">')
        html_parts.append('<main class="thread-content">')

        # Display each group
        for i, group in enumerate(grouped_messages):
            if not group:
                continue
            html_parts.append(self._format_message_group(group, i + 1))

        html_parts.append("</main>")

        # Sidebar with stats (will be populated after processing)
        html_parts.append(self._generate_sidebar(conversation_info))

        html_parts.append("</div>")  # thread-body
        html_parts.append("</article>")

        return "\n".join(html_parts)

    def _extract_title(self, grouped_messages: list[list[dict]]) -> str:
        """Extract a title from the first user message."""
        for group in grouped_messages:
            if not group:
                continue
            first_msg = group[0]
            message_data = first_msg.get("message", {})
            if message_data.get("role") == "user":
                content = message_data.get("content", "")
                if isinstance(content, str):
                    # Take first line, truncate if needed
                    first_line = content.split("\n")[0].strip()
                    if len(first_line) > 80:
                        return first_line[:77] + "..."
                    return first_line if first_line else "Conversation"
                elif isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "text":
                            text = item.get("text", "").strip()
                            first_line = text.split("\n")[0].strip()
                            if len(first_line) > 80:
                                return first_line[:77] + "..."
                            return first_line if first_line else "Conversation"
        return "Conversation"

    def _generate_sidebar(self, conversation_info: dict) -> str:
        """Generate the sidebar with stats."""
        parts = []
        parts.append('<aside class="thread-sidebar">')

        # Thread info section
        parts.append('<section class="sidebar-section">')
        parts.append('<h3 class="sidebar-title">Thread</h3>')
        parts.append('<dl class="sidebar-stats">')

        if conversation_info.get("start_time"):
            parts.append(f'<dt>Created</dt><dd>{humanize_date(conversation_info["start_time"])}</dd>')

        if conversation_info.get("model"):
            # Shorten model name (e.g., "claude-opus-4-5-20251101" -> "Opus 4.5")
            model = conversation_info["model"]
            if "opus" in model.lower():
                model_short = "Opus 4.5"
            elif "sonnet" in model.lower():
                model_short = "Sonnet 4"
            elif "haiku" in model.lower():
                model_short = "Haiku"
            else:
                model_short = model.split("-")[1].title() if "-" in model else model
            parts.append(f"<dt>Model</dt><dd>{model_short}</dd>")

        if conversation_info.get("version"):
            parts.append(f'<dt>CLI</dt><dd>v{conversation_info["version"]}</dd>')

        if conversation_info.get("git_branch"):
            parts.append(f'<dt>Branch</dt><dd>{html.escape(conversation_info["git_branch"])}</dd>')

        parts.append("</dl>")
        parts.append("</section>")

        # Stats section
        parts.append('<section class="sidebar-section">')
        parts.append('<h3 class="sidebar-title">Stats</h3>')
        parts.append('<dl class="sidebar-stats">')

        total_files = len(self.stats["files_read"] | self.stats["files_edited"])
        if total_files > 0:
            parts.append(f"<dt>Files</dt><dd>{total_files}</dd>")

        if self.stats["lines_added"] > 0 or self.stats["lines_removed"] > 0:
            added = f'<span class="lines-added">+{self.stats["lines_added"]}</span>'
            removed = f'<span class="lines-removed">-{self.stats["lines_removed"]}</span>'
            parts.append(f"<dt>Lines</dt><dd>{added} {removed}</dd>")

        if self.stats["tool_calls"] > 0:
            parts.append(f'<dt>Tools</dt><dd>{self.stats["tool_calls"]}</dd>')

        if conversation_info.get("duration_ms", 0) > 0:
            duration_s = conversation_info["duration_ms"] / 1000
            if duration_s >= 3600:
                duration_str = f"{duration_s / 3600:.1f}h"
            elif duration_s >= 60:
                duration_str = f"{duration_s / 60:.1f}m"
            else:
                duration_str = f"{duration_s:.1f}s"
            parts.append(f"<dt>Duration</dt><dd>{duration_str}</dd>")

        parts.append("</dl>")
        parts.append("</section>")

        # Token usage section
        total_tokens = (
            conversation_info.get("input_tokens", 0)
            + conversation_info.get("output_tokens", 0)
            + conversation_info.get("cache_read_tokens", 0)
        )
        if total_tokens > 0:
            parts.append('<section class="sidebar-section">')
            parts.append('<h3 class="sidebar-title">Tokens</h3>')
            parts.append('<dl class="sidebar-stats">')

            if conversation_info.get("input_tokens", 0) > 0:
                parts.append(f'<dt>Input</dt><dd>{conversation_info["input_tokens"]:,}</dd>')

            if conversation_info.get("output_tokens", 0) > 0:
                parts.append(f'<dt>Output</dt><dd>{conversation_info["output_tokens"]:,}</dd>')

            if conversation_info.get("cache_read_tokens", 0) > 0:
                cache = conversation_info["cache_read_tokens"]
                if cache >= 1_000_000:
                    cache_str = f"{cache / 1_000_000:.1f}M"
                elif cache >= 1_000:
                    cache_str = f"{cache / 1_000:.1f}K"
                else:
                    cache_str = str(cache)
                parts.append(f"<dt>Cache</dt><dd>{cache_str}</dd>")

            parts.append("</dl>")
            parts.append("</section>")

        # Files modified section
        edited_files = self.stats["files_edited"]
        if edited_files:
            parts.append('<section class="sidebar-section">')
            parts.append('<h3 class="sidebar-title">Files Modified</h3>')
            parts.append('<ul class="file-list">')
            for f in sorted(edited_files)[:10]:  # Limit to 10
                filename = Path(f).name
                parts.append(f"<li>{html.escape(filename)}</li>")
            if len(edited_files) > 10:
                parts.append(f"<li class='more'>+{len(edited_files) - 10} more</li>")
            parts.append("</ul>")
            parts.append("</section>")

        parts.append("</aside>")
        return "\n".join(parts)

    def _format_message_group(self, messages: list[dict[str, Any]], message_number: int = None) -> str:
        """Format a group of messages from the same role."""
        if not messages:
            return ""

        first_msg = messages[0]
        message_data = first_msg.get("message", {})
        role = message_data.get("role", "unknown")

        message_parts = []

        for msg in messages:
            if msg.get("type") == "tool_result":
                continue

            message_data = msg.get("message", {})
            content = message_data.get("content", "")

            if isinstance(content, str):
                message_parts.append(self._format_text_content(content, role))
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            message_parts.append(self._format_text_content(item.get("text", ""), role))
                        elif item.get("type") == "tool_use":
                            message_parts.append(self._format_tool_use_html(item, msg))

        if not message_parts:
            return ""

        role_class = f"message {role}"

        html_parts = []
        html_parts.append(f'<div class="{role_class}" id="msg-{message_number}">')

        # Message content wrapper
        html_parts.append('<div class="message-content">')

        # Message body (no header needed - avatar indicates role)
        html_parts.append('<div class="message-body">')
        for part in message_parts:
            html_parts.append(part)
        html_parts.append("</div>")

        html_parts.append("</div>")  # message-content
        html_parts.append("</div>")  # message
        return "\n".join(html_parts)

    def _format_text_content(self, content: str, role: str) -> str:
        """Format text content with proper HTML escaping and markdown conversion."""
        if not content.strip():
            return ""

        # Check for thinking blocks (Claude's extended thinking)
        thinking_match = re.search(r"<thinking>(.*?)</thinking>", content, re.DOTALL)
        if thinking_match:
            thinking_content = thinking_match.group(1)
            content = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL)
            thinking_html = self._format_thinking_block(thinking_content)
            if content.strip():
                return thinking_html + self._format_regular_text(content, role)
            return thinking_html

        return self._format_regular_text(content, role)

    def _format_thinking_block(self, content: str) -> str:
        """Format a thinking block as collapsible."""
        escaped = html.escape(content.strip())
        escaped = self._markdown_to_html(escaped)
        return f"""<details class="thinking-block">
<summary class="thinking-summary">Thinking</summary>
<div class="thinking-content">{escaped}</div>
</details>"""

    def _format_regular_text(self, content: str, role: str) -> str:
        """Format regular text content."""
        escaped = html.escape(content)
        escaped = self._markdown_to_html(escaped)

        if role == "user":
            escaped = self._parse_special_tags_html(escaped)
            # Trim long user messages with expandable option
            if len(content) > 300:
                preview = html.escape(content[:280].rsplit(" ", 1)[0])
                preview = self._markdown_to_html(preview)
                return f"""<div class="text-block user-text">
<div class="user-preview">{preview}...</div>
<details class="user-expand"><summary>Show more</summary>
<div class="user-full">{escaped}</div>
</details>
</div>"""

        return f'<div class="text-block">{escaped}</div>'

    def _markdown_to_html(self, content: str) -> str:
        """Convert basic markdown to HTML."""
        # Code blocks first (before inline code)
        content = re.sub(
            r"```(\w*)\n(.*?)```",
            lambda m: f'<pre class="code-block" data-lang="{m.group(1)}"><code>{m.group(2)}</code></pre>',
            content,
            flags=re.DOTALL,
        )

        # Tables - convert markdown tables to HTML
        content = self._convert_tables(content)

        # Bold **text**
        content = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", content)

        # Italic *text*
        content = re.sub(r"\*(.*?)\*", r"<em>\1</em>", content)

        # Inline code `code`
        content = re.sub(r"`(.*?)`", r"<code>\1</code>", content)

        # Headers
        content = re.sub(r"^### (.*?)$", r"<h4>\1</h4>", content, flags=re.MULTILINE)
        content = re.sub(r"^## (.*?)$", r"<h3>\1</h3>", content, flags=re.MULTILINE)
        content = re.sub(r"^# (.*?)$", r"<h2>\1</h2>", content, flags=re.MULTILINE)

        # Convert lists properly
        content = self._convert_lists(content)

        # Line breaks (but not inside code blocks, tables, or lists)
        lines = content.split("\n")
        result = []
        in_code = False
        for line in lines:
            if "<pre" in line:
                in_code = True
            if "</pre>" in line:
                in_code = False
            if not in_code and line.strip():
                result.append(line)
            elif in_code:
                result.append(line)
            else:
                result.append("<br>")
        content = "\n".join(result)

        return content

    def _convert_lists(self, content: str) -> str:
        """Convert markdown lists to HTML lists."""
        lines = content.split("\n")
        result = []
        list_items = []
        list_type = None  # 'ul' or 'ol'

        for line in lines:
            stripped = line.strip()

            # Check for unordered list item (- or *)
            ul_match = re.match(r"^[-*]\s+(.+)$", stripped)
            # Check for ordered list item (1. 2. etc)
            ol_match = re.match(r"^\d+\.\s+(.+)$", stripped)

            if ul_match:
                if list_type == "ol" and list_items:
                    # Close previous ordered list
                    result.append("<ol>" + "".join(list_items) + "</ol>")
                    list_items = []
                list_type = "ul"
                list_items.append(f"<li>{ul_match.group(1)}</li>")
            elif ol_match:
                if list_type == "ul" and list_items:
                    # Close previous unordered list
                    result.append("<ul>" + "".join(list_items) + "</ul>")
                    list_items = []
                list_type = "ol"
                list_items.append(f"<li>{ol_match.group(1)}</li>")
            else:
                # Not a list item - close any open list
                if list_items:
                    tag = list_type or "ul"
                    result.append(f"<{tag}>" + "".join(list_items) + f"</{tag}>")
                    list_items = []
                    list_type = None
                result.append(line)

        # Close any remaining list
        if list_items:
            tag = list_type or "ul"
            result.append(f"<{tag}>" + "".join(list_items) + f"</{tag}>")

        return "\n".join(result)

    def _convert_tables(self, content: str) -> str:
        """Convert markdown tables to HTML tables."""
        lines = content.split("\n")
        result = []
        table_lines = []
        in_table = False

        for line in lines:
            # Check if line looks like a table row (starts and ends with |)
            stripped = line.strip()
            is_table_row = stripped.startswith("|") and stripped.endswith("|")

            if is_table_row:
                if not in_table:
                    in_table = True
                table_lines.append(stripped)
            else:
                if in_table:
                    # End of table, convert it
                    result.append(self._table_to_html(table_lines))
                    table_lines = []
                    in_table = False
                result.append(line)

        # Handle table at end of content
        if in_table and table_lines:
            result.append(self._table_to_html(table_lines))

        return "\n".join(result)

    def _table_to_html(self, table_lines: list[str]) -> str:
        """Convert table lines to HTML table."""
        if len(table_lines) < 2:
            return "\n".join(table_lines)

        html_parts = ['<table class="md-table">']

        for i, line in enumerate(table_lines):
            # Skip separator line (contains only -, |, :, and spaces)
            if re.match(r"^\|[\s\-:|]+\|$", line):
                continue

            # Parse cells
            cells = [cell.strip() for cell in line.split("|")[1:-1]]

            if i == 0:
                # Header row
                html_parts.append("<thead><tr>")
                for cell in cells:
                    html_parts.append(f"<th>{cell}</th>")
                html_parts.append("</tr></thead><tbody>")
            else:
                # Body row
                html_parts.append("<tr>")
                for cell in cells:
                    html_parts.append(f"<td>{cell}</td>")
                html_parts.append("</tr>")

        html_parts.append("</tbody></table>")
        return "".join(html_parts)

    def _parse_special_tags_html(self, content: str) -> str:
        """Parse special tags in content for HTML."""
        content = re.sub(
            r"&lt;command-message&gt;(.*?)&lt;/command-message&gt;",
            r'<span class="command-message">\1</span>',
            content,
            flags=re.DOTALL,
        )
        content = re.sub(
            r"&lt;command-name&gt;(.*?)&lt;/command-name&gt;",
            r'<span class="command-name">\1</span>',
            content,
            flags=re.DOTALL,
        )
        content = re.sub(
            r"&lt;system-reminder&gt;(.*?)&lt;/system-reminder&gt;",
            r'<details class="system-reminder"><summary>System Reminder</summary>\1</details>',
            content,
            flags=re.DOTALL,
        )
        return content

    def _format_tool_use_html(self, tool_use: dict[str, Any], msg: dict[str, Any]) -> str:
        """Format a tool use block with its result for HTML."""
        tool_name = tool_use.get("name", "Unknown Tool")
        tool_id = tool_use.get("id")

        self.stats["tool_calls"] += 1

        tool_result = None
        if tool_id:
            msg_uuid = msg.get("uuid")
            if msg_uuid and msg_uuid in self._tool_results:
                tool_result = self._tool_results[msg_uuid]
            elif tool_id in self._tool_results:
                tool_result = self._tool_results[tool_id]

        return self.format_tool_use(tool_name, tool_use, tool_result)

    def format_tool_use(self, tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use with the appropriate HTML formatter."""
        formatter = HTML_TOOL_FORMATTERS.get(tool_name)

        if formatter:
            return formatter.format(tool_use, tool_result, self.stats)
        else:
            return f'<div class="tool-pill unknown"><span class="tool-icon">⚙</span> {html.escape(tool_name)}</div>'


class HTMLToolFormatter:
    """Base class for HTML tool formatters."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        """Format a tool use and its result as HTML."""
        raise NotImplementedError


class HTMLBashFormatter(HTMLToolFormatter):
    """Format Bash tool usage - terminal command style."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        command = input_data.get("command", "unknown command")

        if stats:
            stats["bash_commands"] += 1

        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        # Calculate line count from output
        line_count = 0
        if result_text and str(result_text).strip():
            line_count = len(str(result_text).strip().split("\n"))

        parts = []
        parts.append('<details class="terminal-block">')
        parts.append('<summary class="terminal-header">')
        parts.append('<span class="terminal-prompt">&gt;_</span>')
        parts.append(f'<code class="terminal-command">{html.escape(command)}</code>')
        if line_count > 0:
            parts.append(f'<span class="line-count">{line_count} lines</span>')
        parts.append("</summary>")

        if result_text and str(result_text).strip():
            parts.append(f'<pre class="terminal-output">{html.escape(str(result_text).strip())}</pre>')

        parts.append("</details>")
        return "\n".join(parts)


class HTMLReadFormatter(HTMLToolFormatter):
    """Format Read tool usage - file pill style."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        offset = input_data.get("offset", "")
        limit = input_data.get("limit", "")

        if stats:
            stats["files_read"].add(file_path)

        filename = Path(file_path).name
        line_info = ""
        if offset or limit:
            line_info = f" L{offset or 1}-{(offset or 0) + (limit or 100)}"

        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        line_count = len(str(result_text).split("\n")) if result_text else 0

        parts = []
        parts.append('<details class="tool-pill read-pill">')
        parts.append(
            f'<summary><span class="pill-icon">📄</span> <span class="pill-file">{html.escape(filename)}</span>'
        )
        parts.append(f'<span class="pill-meta">{line_info} {line_count} lines</span></summary>')

        if result_text:
            parts.append(f'<pre class="file-content">{html.escape(str(result_text).strip())}</pre>')

        parts.append("</details>")
        return "\n".join(parts)


class HTMLEditFormatter(HTMLToolFormatter):
    """Format Edit tool usage - diff block style."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        old_string = input_data.get("old_string", "")
        new_string = input_data.get("new_string", "")

        if stats:
            stats["files_edited"].add(file_path)
            old_lines = len(old_string.split("\n")) if old_string else 0
            new_lines = len(new_string.split("\n")) if new_string else 0
            stats["lines_added"] += max(0, new_lines - old_lines) if new_lines > old_lines else new_lines
            stats["lines_removed"] += max(0, old_lines - new_lines) if old_lines > new_lines else old_lines

        filename = Path(file_path).name
        old_lines = old_string.split("\n") if old_string else []
        new_lines = new_string.split("\n") if new_string else []

        added_count = len(new_lines)
        removed_count = len(old_lines)
        total_lines = added_count + removed_count

        parts = []
        parts.append('<details class="diff-block">')
        parts.append('<summary class="diff-header">')
        parts.append('<span class="diff-icon">📝</span>')
        parts.append(f'<span class="diff-file">{html.escape(filename)}</span>')
        parts.append(f'<span class="diff-added">+{added_count}</span>')
        parts.append(f'<span class="diff-removed">-{removed_count}</span>')
        parts.append(f'<span class="line-count">{total_lines} lines</span>')
        parts.append("</summary>")

        parts.append('<div class="diff-content">')
        for line in old_lines:
            parts.append(f'<div class="diff-line removed">- {html.escape(line)}</div>')
        for line in new_lines:
            parts.append(f'<div class="diff-line added">+ {html.escape(line)}</div>')
        parts.append("</div>")

        parts.append("</details>")
        return "\n".join(parts)


class HTMLMultiEditFormatter(HTMLToolFormatter):
    """Format MultiEdit tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        edits = input_data.get("edits", [])

        if stats:
            stats["files_edited"].add(file_path)

        filename = Path(file_path).name

        parts = []
        parts.append('<details class="diff-block multi">')
        parts.append('<summary class="diff-header">')
        parts.append('<span class="diff-icon">📝</span>')
        parts.append(f'<span class="diff-file">{html.escape(filename)}</span>')
        parts.append(f'<span class="diff-lines">{len(edits)} edits</span>')
        parts.append("</summary>")

        for i, edit in enumerate(edits, 1):
            old_string = edit.get("old_string", "")
            new_string = edit.get("new_string", "")

            if stats:
                old_lines = len(old_string.split("\n")) if old_string else 0
                new_lines = len(new_string.split("\n")) if new_string else 0
                stats["lines_added"] += new_lines
                stats["lines_removed"] += old_lines

            parts.append(f'<div class="diff-section"><span class="edit-num">Edit {i}</span>')
            parts.append('<div class="diff-content">')
            for line in old_string.split("\n") if old_string else []:
                parts.append(f'<div class="diff-line removed">- {html.escape(line)}</div>')
            for line in new_string.split("\n") if new_string else []:
                parts.append(f'<div class="diff-line added">+ {html.escape(line)}</div>')
            parts.append("</div></div>")

        parts.append("</details>")
        return "\n".join(parts)


class HTMLGrepFormatter(HTMLToolFormatter):
    """Format Grep tool usage - search pill style."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        pattern = input_data.get("pattern", "unknown pattern")
        path = input_data.get("path", ".")

        if stats:
            stats["searches"] += 1

        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        match_count = 0
        if result_text:
            lines = [line for line in str(result_text).strip().split("\n") if line.strip()]
            match_count = len(lines)

        path_display = Path(path).name if path != "." else "project"

        parts = []
        parts.append('<details class="tool-pill search-pill">')
        parts.append(
            f'<summary><span class="pill-icon">🔍</span> <code class="pill-query">{html.escape(pattern)}</code>'
        )
        parts.append(f'<span class="pill-meta">{match_count} matches in {html.escape(path_display)}</span></summary>')

        if result_text and match_count > 0:
            parts.append('<div class="search-results">')
            for line in str(result_text).strip().split("\n")[:20]:
                if line.strip():
                    parts.append(f'<div class="search-result">{html.escape(line)}</div>')
            if match_count > 20:
                parts.append(f'<div class="search-more">+{match_count - 20} more matches</div>')
            parts.append("</div>")

        parts.append("</details>")
        return "\n".join(parts)


class HTMLWriteFormatter(HTMLToolFormatter):
    """Format Write tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        content = input_data.get("content", "")

        if stats:
            stats["files_edited"].add(file_path)
            stats["lines_added"] += len(content.split("\n")) if content else 0

        filename = Path(file_path).name
        line_count = len(content.split("\n")) if content else 0

        parts = []
        parts.append('<details class="tool-pill write-pill">')
        parts.append(
            f'<summary><span class="pill-icon">💾</span> <span class="pill-file">{html.escape(filename)}</span>'
        )
        parts.append(f'<span class="pill-meta">+{line_count} lines (new file)</span></summary>')

        if content:
            preview = "\n".join(content.split("\n")[:20])
            parts.append(f'<pre class="file-content">{html.escape(preview)}</pre>')
            if line_count > 20:
                parts.append(f'<div class="file-more">+{line_count - 20} more lines</div>')

        parts.append("</details>")
        return "\n".join(parts)


class HTMLTaskFormatter(HTMLToolFormatter):
    """Format Task/Agent tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        description = input_data.get("description", input_data.get("prompt", "Task"))

        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        parts = []
        parts.append('<details class="tool-pill task-pill">')
        parts.append(
            f'<summary><span class="pill-icon">🤖</span> <span class="pill-task">{html.escape(description)}</span></summary>'
        )

        if result_text:
            parts.append(f'<div class="task-result">{html.escape(str(result_text)[:500])}</div>')

        parts.append("</details>")
        return "\n".join(parts)


class HTMLTodoFormatter(HTMLToolFormatter):
    """Format TodoWrite tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None, stats: dict = None) -> str:
        input_data = tool_use.get("input", {})
        todos = input_data.get("todos", [])

        parts = []
        parts.append('<div class="todo-block">')
        parts.append('<div class="todo-header"><span class="pill-icon">📋</span> Todos</div>')
        parts.append('<ul class="todo-list">')

        for todo in todos[:8]:
            content = todo.get("content", "")
            status = todo.get("status", "pending")
            icon = "✓" if status == "completed" else "○" if status == "pending" else "◐"
            status_class = status
            parts.append(
                f'<li class="todo-item {status_class}"><span class="todo-icon">{icon}</span> {html.escape(content)}</li>'
            )

        if len(todos) > 8:
            parts.append(f'<li class="todo-more">+{len(todos) - 8} more</li>')

        parts.append("</ul>")
        parts.append("</div>")
        return "\n".join(parts)


# Registry of HTML tool formatters
HTML_TOOL_FORMATTERS = {
    "Bash": HTMLBashFormatter(),
    "Read": HTMLReadFormatter(),
    "Write": HTMLWriteFormatter(),
    "Edit": HTMLEditFormatter(),
    "MultiEdit": HTMLMultiEditFormatter(),
    "Grep": HTMLGrepFormatter(),
    "Task": HTMLTaskFormatter(),
    "TodoWrite": HTMLTodoFormatter(),
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
        pass
    return ""


def get_html_css() -> str:
    """Return CSS styles for HTML output - nof1 terminal aesthetic with ampcode features."""
    return """
<style>
@import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@300;400;500;600;700&display=swap");

:root {
    /* nof1 light theme - clean terminal aesthetic */
    --bg: #ffffff;
    --bg-elevated: #fafafa;
    --bg-subtle: #f5f5f5;
    --fg: #000000;
    --fg-muted: #666666;
    --fg-subtle: #999999;
    --border: #cccccc;
    --border-muted: #e0e0e0;
    --accent: #000000;
    --accent-emphasis: #000000;
    --success: #006600;
    --success-subtle: rgba(0, 102, 0, 0.1);
    --danger: #cc0000;
    --danger-subtle: rgba(204, 0, 0, 0.1);
    --warning: #996600;
    --warning-subtle: rgba(153, 102, 0, 0.1);
}

[data-theme="dark"] {
    --bg: #000000;
    --bg-elevated: #0a0a0a;
    --bg-subtle: #111111;
    --fg: #ffffff;
    --fg-muted: #888888;
    --fg-subtle: #555555;
    --border: #333333;
    --border-muted: #222222;
    --accent: #ffffff;
    --accent-emphasis: #ffffff;
    --success: #00ff00;
    --success-subtle: rgba(0, 255, 0, 0.1);
    --danger: #ff3333;
    --danger-subtle: rgba(255, 51, 51, 0.1);
    --warning: #ffcc00;
    --warning-subtle: rgba(255, 204, 0, 0.1);
}

*, *::before, *::after {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

html {
    font-size: 14px;
}

body {
    font-family: "IBM Plex Mono", monospace;
    background: var(--bg);
    color: var(--fg);
    line-height: 1.6;
    -webkit-font-smoothing: antialiased;
    position: relative;
}

/* nof1 noise texture overlay */
body::before {
    content: "";
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    opacity: 0.03;
    z-index: 1000;
    background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E");
}

/* Thread Layout */
.thread {
    max-width: 1400px;
    margin: 0 auto;
    padding: 48px 32px;
}

.thread-header {
    margin-bottom: 48px;
    padding-bottom: 32px;
    border-bottom: 1px solid var(--border);
}

.thread-title {
    font-size: 1.25rem;
    font-weight: 500;
    color: var(--fg);
    margin-bottom: 16px;
    line-height: 1.4;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.thread-meta {
    display: flex;
    gap: 24px;
    color: var(--fg-muted);
    font-size: 0.75rem;
    text-transform: uppercase;
    letter-spacing: 0.15em;
}

.meta-item::before {
    content: "/";
    margin-right: 24px;
    color: var(--border);
}

.meta-item:first-child::before {
    display: none;
}

/* Two-column layout */
.thread-body {
    display: grid;
    grid-template-columns: 1fr 260px;
    gap: 48px;
}

@media (max-width: 1000px) {
    .thread-body {
        grid-template-columns: 1fr;
    }
    .thread-sidebar {
        order: -1;
    }
}

.thread-content {
    min-width: 0;
}

/* Sidebar - nof1 style */
.thread-sidebar {
    position: sticky;
    top: 32px;
    height: fit-content;
}

.sidebar-section {
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 20px;
    margin-bottom: 20px;
}

.sidebar-title {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--fg-muted);
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-muted);
}

.sidebar-stats {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 12px 20px;
    font-size: 0.8rem;
}

.sidebar-stats dt {
    color: var(--fg-muted);
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.7rem;
}

.sidebar-stats dd {
    text-align: right;
    font-weight: 500;
    font-family: "IBM Plex Mono", monospace;
}

.sidebar-stats .lines-added {
    color: var(--success);
}

.sidebar-stats .lines-removed {
    color: var(--danger);
}

.file-list {
    list-style: none;
    font-size: 0.75rem;
}

.file-list li {
    padding: 8px 0;
    color: var(--fg-muted);
    border-bottom: 1px solid var(--border-muted);
    font-family: "IBM Plex Mono", monospace;
}

.file-list li:last-child {
    border-bottom: none;
}

.file-list .more {
    color: var(--fg-subtle);
    font-style: italic;
}

/* Role separator - visual break between conversation turns */
.role-separator {
    border: none;
    border-top: 1px solid var(--border);
    margin: 32px 0;
    position: relative;
}

.role-separator::after {
    content: "•";
    position: absolute;
    left: 50%;
    top: -0.5em;
    transform: translateX(-50%);
    background: var(--bg);
    padding: 0 12px;
    color: var(--border);
    font-size: 0.8rem;
}

/* Messages - hybrid chat layout */
.message {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
}

/* User messages - right-aligned bubbles */
.message.user {
    justify-content: flex-end;
    margin-bottom: 20px;
}

.message.user .message-content {
    max-width: 70%;
    background: var(--fg);
    color: var(--bg);
    border-radius: 16px 16px 4px 16px;
    padding: 12px 16px;
}

.message.user .message-content code {
    background: rgba(255,255,255,0.2);
    color: var(--bg);
}

.message.user .text-block {
    margin-bottom: 0;
}

/* User text - trimmed with expand */
.user-text .user-preview {
    display: block;
}

.user-text .user-expand {
    margin-top: 8px;
}

.user-text .user-expand summary {
    cursor: pointer;
    opacity: 0.7;
    font-size: 0.8rem;
}

.user-text .user-expand[open] .user-preview {
    display: none;
}

.user-text .user-expand[open] + .user-preview,
.user-text:has(.user-expand[open]) .user-preview {
    display: none;
}

.user-text .user-full {
    margin-top: 8px;
}

/* Assistant messages - left-aligned with border bubble */
.message.assistant {
    justify-content: flex-start;
    margin-bottom: 20px;
}

.message.assistant .message-content {
    max-width: 85%;
    border: 1px solid var(--border);
    border-radius: 16px 16px 16px 4px;
    padding: 16px 20px;
}

.message-content {
    min-width: 0;
}

.message-body {
    /* Content flows naturally */
}

/* Text content */
.text-block {
    margin-bottom: 12px;
    line-height: 1.5;
}

.text-block h2, .text-block h3, .text-block h4 {
    margin: 16px 0 8px 0;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.text-block code {
    background: var(--bg-elevated);
    font-size: 0.9em;
}

.text-block strong {
    font-weight: 600;
}

.text-block ul,
.text-block ol {
    margin: 12px 0;
    padding-left: 24px;
}

.text-block li {
    margin-bottom: 6px;
    line-height: 1.5;
}

/* Markdown tables */
.md-table {
    width: 100%;
    border-collapse: collapse;
    margin: 16px 0;
    font-size: 0.85rem;
}

.md-table th,
.md-table td {
    border: 1px solid var(--border);
    padding: 8px 12px;
    text-align: left;
}

.md-table th {
    background: var(--bg-elevated);
    font-weight: 600;
    text-transform: uppercase;
    font-size: 0.75rem;
    letter-spacing: 0.05em;
}

.md-table tr:hover {
    background: var(--bg-subtle);
}

.code-block {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    padding: 12px;
    overflow-x: auto;
    margin: 8px 0;
    font-size: 0.8rem;
    font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Droid Sans Mono", "Source Code Pro", ui-monospace, monospace;
}

/* Thinking block */
.thinking-block {
    background: var(--bg);
    border: 1px solid var(--border);
    margin: 8px 0;
}

.thinking-summary {
    padding: 8px 12px;
    cursor: pointer;
    font-weight: 500;
    color: var(--fg-muted);
    display: flex;
    align-items: center;
    gap: 8px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.65rem;
}

.thinking-summary::before {
    content: "▶";
    font-size: 0.6em;
    transition: transform 0.2s;
}

.thinking-block[open] .thinking-summary::before {
    transform: rotate(90deg);
}

.thinking-content {
    padding: 0 12px 12px;
    border-top: 1px solid var(--border);
    color: var(--fg-muted);
    font-size: 0.8rem;
}

/* Tool Pills */
.tool-pill {
    background: var(--bg);
    border: 1px solid var(--border);
    margin: 10px 0;
    font-size: 0.8rem;
    transition: border-color 0.15s ease;
}

.tool-pill:hover {
    border-color: var(--fg-muted);
}

.tool-pill summary {
    padding: 10px 14px;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 10px;
    list-style: none;
}

.tool-pill summary::-webkit-details-marker {
    display: none;
}

.pill-icon {
    font-size: 0.9em;
    opacity: 0.7;
}

.pill-file, .pill-task {
    font-weight: 500;
    color: var(--fg);
}

.pill-query {
    background: var(--bg-elevated);
    border: 1px solid var(--border-muted);
    padding: 4px 8px;
}

.pill-meta {
    color: var(--fg-subtle);
    margin-left: auto;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.tool-pill .file-content,
.tool-pill .search-results,
.tool-pill .task-result {
    padding: 12px 14px;
    border-top: 1px solid var(--border);
    background: var(--bg-elevated);
    font-size: 0.75rem;
    max-height: 300px;
    overflow: auto;
    font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Droid Sans Mono", "Source Code Pro", ui-monospace, monospace;
}

.search-result {
    padding: 4px 0;
    border-bottom: 1px solid var(--border-muted);
}

.search-more, .file-more {
    padding-top: 8px;
    color: var(--fg-subtle);
    font-style: italic;
}

/* Terminal Block - collapsible like diff */
.terminal-block {
    background: var(--bg);
    border: 1px solid var(--border);
    margin: 10px 0;
    overflow: hidden;
    transition: border-color 0.15s ease;
}

.terminal-block:hover {
    border-color: var(--fg-muted);
}

.terminal-block > .terminal-header {
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--bg-elevated);
    cursor: pointer;
    list-style: none;
}

.terminal-block > .terminal-header::-webkit-details-marker {
    display: none;
}

.terminal-prompt {
    color: var(--success);
    font-weight: 600;
    font-size: 0.8rem;
}

.terminal-command {
    color: var(--fg);
    font-size: 0.8rem;
}

.terminal-output {
    padding: 12px 14px;
    font-size: 0.75rem;
    background: var(--bg);
    margin: 0;
    max-height: 300px;
    overflow: auto;
    color: var(--fg-muted);
    font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Droid Sans Mono", "Source Code Pro", ui-monospace, monospace;
}

/* Line count - right-aligned */
.line-count {
    margin-left: auto;
    color: var(--fg-subtle);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    white-space: nowrap;
}

/* Diff Block - collapsible */
.diff-block {
    background: var(--bg);
    border: 1px solid var(--border);
    margin: 10px 0;
    overflow: hidden;
    transition: border-color 0.15s ease;
}

.diff-block:hover {
    border-color: var(--fg-muted);
}

.diff-block > .diff-header {
    padding: 10px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    background: var(--bg-elevated);
    cursor: pointer;
    list-style: none;
}

.diff-block > .diff-header::-webkit-details-marker {
    display: none;
}

.diff-icon {
    font-size: 0.9em;
    opacity: 0.7;
}

.diff-file {
    font-weight: 500;
    color: var(--fg);
    font-size: 0.85rem;
}

.diff-added {
    color: var(--success);
    font-size: 0.75rem;
    font-weight: 600;
}

.diff-removed {
    color: var(--danger);
    font-size: 0.75rem;
    font-weight: 600;
}


.diff-content {
    padding: 8px 0;
    font-size: 0.75rem;
    font-family: "SF Mono", "Monaco", "Inconsolata", "Fira Mono", "Droid Sans Mono", "Source Code Pro", ui-monospace, monospace;
}

.diff-line {
    padding: 3px 14px;
    white-space: pre-wrap;
    word-break: break-all;
}

.diff-line.removed {
    background: var(--danger-subtle);
    color: var(--danger);
}

.diff-line.added {
    background: var(--success-subtle);
    color: var(--success);
}

.diff-progress {
    height: 2px;
    background: var(--success);
}

.diff-section {
    border-top: 1px solid var(--border);
    padding-top: 12px;
}

.edit-num {
    display: block;
    padding: 8px 16px;
    font-size: 0.7rem;
    color: var(--fg-muted);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

/* Todo Block */
.todo-block {
    background: var(--bg);
    border: 1px solid var(--border);
    margin: 6px 0;
    padding: 10px 12px;
    transition: border-color 0.15s ease;
}

.todo-block:hover {
    border-color: var(--fg-muted);
}

.todo-header {
    font-weight: 500;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.65rem;
    color: var(--fg-muted);
}

.todo-list {
    list-style: none;
}

.todo-item {
    padding: 4px 0;
    display: flex;
    align-items: center;
    gap: 8px;
    border-bottom: 1px solid var(--border-muted);
    font-size: 0.8rem;
}

.todo-item:last-child {
    border-bottom: none;
}

.todo-icon {
    width: 16px;
    text-align: center;
}

.todo-item.completed {
    color: var(--fg-muted);
}

.todo-item.completed .todo-icon {
    color: var(--success);
}

.todo-item.in_progress .todo-icon {
    color: var(--warning);
}

.todo-more {
    padding-top: 12px;
    color: var(--fg-subtle);
    font-style: italic;
}

/* Special tags */
.command-message {
    font-style: italic;
    color: var(--fg-muted);
}

.command-name {
    font-weight: 600;
    color: var(--fg);
}

.system-reminder {
    background: var(--bg);
    border: 1px solid var(--warning);
    margin: 16px 0;
}

.system-reminder summary {
    padding: 12px 16px;
    cursor: pointer;
    color: var(--warning);
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    font-size: 0.7rem;
}

.system-reminder > div {
    padding: 0 16px 16px;
    font-size: 0.85rem;
}

/* Container */
.container {
    max-width: 1400px;
    margin: 0 auto;
}

/* Theme toggle - nof1 style */
.theme-toggle {
    position: fixed;
    top: 20px;
    right: 20px;
    z-index: 100;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--fg);
    padding: 10px 16px;
    font-family: "IBM Plex Mono", monospace;
    font-size: 0.65rem;
    cursor: pointer;
    text-transform: uppercase;
    letter-spacing: 0.2em;
}

.theme-toggle:hover {
    background: var(--fg);
    color: var(--bg);
}

/* Back to top */
.back-to-top {
    text-align: center;
    padding: 48px 0;
    border-top: 1px solid var(--border);
    margin-top: 48px;
}

.back-to-top a {
    color: var(--fg-muted);
    text-decoration: none;
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.2em;
}

.back-to-top a:hover {
    color: var(--fg);
}

/* Conversation nav */
.conversation-nav {
    background: var(--bg);
    border: 1px solid var(--border);
    padding: 24px;
    margin-bottom: 48px;
}

.conversation-nav h2 {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.2em;
    color: var(--fg-muted);
    margin-bottom: 20px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-muted);
}

.conversation-toc {
    list-style: none;
}

.conversation-toc li {
    margin-bottom: 8px;
}

.conversation-toc a {
    display: block;
    padding: 12px 16px;
    background: var(--bg);
    border: 1px solid var(--border);
    color: var(--fg);
    text-decoration: none;
    font-size: 0.8rem;
}

.conversation-toc a:hover {
    background: var(--fg);
    color: var(--bg);
}

/* Scrollbar - minimal */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}

::-webkit-scrollbar-track {
    background: var(--bg);
}

::-webkit-scrollbar-thumb {
    background: var(--border);
}

::-webkit-scrollbar-thumb:hover {
    background: var(--fg-subtle);
}

/* Print */
@media print {
    .theme-toggle, .thread-sidebar {
        display: none;
    }
    .thread-body {
        grid-template-columns: 1fr;
    }
    body::before {
        display: none;
    }
}
</style>
"""
