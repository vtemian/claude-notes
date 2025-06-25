"""Terminal formatter for Claude conversations."""

import re
from typing import Any

from rich.console import Console
from rich.markdown import Markdown

from claude_notes.formatters.base import BaseFormatter
from claude_notes.formatters.tools import format_tool_use


class TerminalFormatter(BaseFormatter):
    """Format Claude conversations for terminal display."""

    def __init__(self, console: Console | None = None):
        """Initialize the formatter."""
        super().__init__()
        self.console = console or Console()

    def format_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> str:
        """Format and return a conversation as a string."""
        # Note: For terminal formatter, we still need to handle the direct console output
        # This method is kept for compatibility with the base class
        # The actual display logic is in display_conversation
        return ""

    def display_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> None:
        """Format and display a conversation to the console."""
        # Display conversation header
        self._display_header(conversation_info)

        # Create a map for tool results
        self._collect_tool_results(messages)

        # Group messages by role continuity
        grouped_messages = self._group_messages(messages)

        # Display each group - each group gets a bullet since they represent role changes
        for group in grouped_messages:
            self._display_message_group(group)

    def format_tool_use(self, tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use with the appropriate formatter."""
        return format_tool_use(tool_name, tool_use, tool_result)

    def _display_header(self, info: dict[str, Any]) -> None:
        """Display conversation header."""
        # Don't display any header - just start with the conversation content
        pass

    def _display_message_group(self, messages: list[dict[str, Any]]) -> None:
        """Display a group of messages from the same role."""
        if not messages:
            return

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
                # Tool results are already handled by the tool formatter
                # Skip them here to avoid duplication
                continue

            message_data = msg.get("message", {})
            content = message_data.get("content", "")

            if isinstance(content, str):
                msg_content.append(content)
            elif isinstance(content, list):
                # Handle content array (e.g., text + tool uses)
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            msg_content.append(self._format_text_content(item.get("text", "")))
                        elif item.get("type") == "tool_use":
                            msg_content.append(self._format_tool_use(item, msg))

            # Join content for this message
            if msg_content:
                message_parts.append("".join(msg_content))

            # Don't add timestamps - keep it clean like Claude

        # Handle mixed content with Rich markup
        if not message_parts:
            return

        # Add spacing before message group
        self.console.print()

        # All other messages are indented without bullets
        prefix = "  "
        indent = "  "  # All lines are indented

        # Display each part with proper indentation
        for i, part in enumerate(message_parts):
            if i > 0:
                self.console.print()  # Add spacing between parts

            # Check if this part contains Rich markup (specifically Rich console markup)
            # Look for Rich markup patterns like [bold red] but not markdown like [link](url)
            rich_markup_pattern = (
                r"\[(?:bold|dim|italic|underline|red|green|blue|cyan|magenta|yellow|white|black)\b[^\]]*\]"
            )
            has_rich_markup = bool(re.search(rich_markup_pattern, part))

            if has_rich_markup:
                self.console.print(f"{indent}{part}")
            else:
                # Plain content or markdown - use markdown formatting
                if role == "user":
                    # Parse special tags first for user messages
                    part = self._parse_special_tags(part)

                # Always try markdown formatting for content without Rich markup
                try:
                    # Subsequent parts get indented
                    self.console.print(f"{indent}", end="")
                    markdown = Markdown(part)
                    self.console.print(markdown)
                except Exception:
                    # Fallback to plain text if markdown parsing fails
                    if i == 0:
                        if role != "user" and role != "assistant":
                            self.console.print(f"{prefix}[dim]{role}:[/dim] {part}")
                        else:
                            self.console.print(f"{prefix}{part}")
                    else:
                        if role != "user" and role != "assistant":
                            self.console.print(f"{indent}[dim]{role}:[/dim] {part}")
                        else:
                            self.console.print(f"{indent}{part}")

    def _parse_special_tags(self, content: str) -> str:
        """Parse special tags in content."""
        # Handle command tags

        # Replace command-message tags
        content = re.sub(
            r"<command-message>(.*?)</command-message>", r"[dim italic]\1[/dim italic]", content, flags=re.DOTALL
        )

        # Replace command-name tags
        content = re.sub(r"<command-name>(.*?)</command-name>", r"[bold cyan]\1[/bold cyan]", content, flags=re.DOTALL)

        # Replace system-reminder tags
        content = re.sub(
            r"<system-reminder>(.*?)</system-reminder>",
            r"[dim yellow]System: \1[/dim yellow]",
            content,
            flags=re.DOTALL,
        )

        return content

    def _format_assistant_content(self, content: str) -> None:
        """Format assistant content with markdown formatting."""
        # Use Rich's Markdown formatter for proper rendering
        try:
            markdown = Markdown(content)
            self.console.print(markdown)
        except Exception:
            # Fallback to plain text if markdown parsing fails
            self.console.print(content)

    def _format_text_content(self, content: str) -> str:
        return "\n[bold white]⏺[/bold white] " + content.strip() if content.strip() else ""

    def _format_tool_use(self, tool_use: dict[str, Any], msg: dict[str, Any]) -> str:
        """Format a tool use block with its result."""
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
        return f"\n{format_tool_use(tool_name, tool_use, tool_result)}"
