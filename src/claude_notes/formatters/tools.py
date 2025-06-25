"""Tool-specific formatters for Claude conversations."""

from pathlib import Path
from typing import Any


class ToolFormatter:
    """Base class for tool formatters."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use and its result."""
        raise NotImplementedError


class BashFormatter(ToolFormatter):
    """Format Bash tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format Bash command and output."""
        input_data = tool_use.get("input", {})
        command = input_data.get("command", "unknown command")

        # Truncate very long commands
        display_command = command
        if len(command) > 80:
            display_command = command[:77] + "..."

        # Format the command line
        formatted = f"[bold red]⏺[/bold red] [bold cyan]Bash[/bold cyan]([yellow]{display_command}[/yellow])"

        # Handle both string and dict formats for tool_result
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and str(result_text).strip():
            lines = str(result_text).strip().split("\n")
            # Filter out empty lines
            lines = [line for line in lines if line.strip()]

            if not lines:
                return formatted

            if len(lines) <= 4:
                # Show all lines if 4 or fewer
                for line in lines:
                    # Truncate very long lines
                    if len(line) > 80:
                        line = line[:77] + "..."
                    formatted += f"\n  [dim]⎿[/dim]  {line}"
            else:
                # Show first 3 lines and indicate more
                for line in lines[:3]:
                    if len(line) > 80:
                        line = line[:77] + "..."
                    formatted += f"\n  [dim]⎿[/dim]  {line}"
                formatted += f"\n\n     [dim]… +{len(lines) - 3} lines (ctrl+r to expand)[/dim]"

        return formatted


class ReadFormatter(ToolFormatter):
    """Format Read tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format file read operation."""
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")

        # Extract just the filename
        filename = Path(file_path).name

        formatted = f"[bold green]📄[/bold green] [bold cyan]Read[/bold cyan]([yellow]{filename}[/yellow])"

        if tool_result:
            # Handle both string and dict formats for tool_result
            result_text = tool_result
            if isinstance(tool_result, dict) and "text" in tool_result:
                result_text = tool_result["text"]

            lines = str(result_text).strip().split("\n")
            line_count = len(lines)

            if line_count <= 10:
                # Show preview for small files
                formatted += f" [dim]({line_count} lines)[/dim]\n"
                for line in lines[:5]:
                    if len(line) > 80:
                        line = line[:77] + "..."
                    formatted += f"  [dim]│[/dim] {line}\n"
                if line_count > 5:
                    formatted += "  [dim]│[/dim] ...\n"
            else:
                formatted += f" [dim]({line_count} lines)[/dim]"

        return formatted


class WriteFormatter(ToolFormatter):
    """Format Write tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format file write operation."""
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        content = input_data.get("content", "")

        filename = Path(file_path).name
        lines = content.split("\n")

        formatted = f"[bold blue]💾[/bold blue] [bold cyan]Write[/bold cyan]([yellow]{filename}[/yellow])"
        formatted += f" [dim]({len(lines)} lines)[/dim]"

        # Handle success check for both formats
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and "successfully" in str(result_text).lower():
            formatted += " [green]✓[/green]"

        # Show a few lines of the content being written (all additions)
        if lines and len(lines) <= 10:
            for line in lines[:5]:
                if line.strip():  # Skip empty lines
                    display_line = line[:60] + "..." if len(line) > 60 else line
                    formatted += f"\n  [dim]⎿[/dim]  [green]+[/green] {display_line}"
            if len(lines) > 5:
                formatted += f"\n     [dim]… +{len(lines) - 5} more lines[/dim]"
        elif lines:
            formatted += f" [green](+{len(lines)} lines)[/green]"

        return formatted


class EditFormatter(ToolFormatter):
    """Format Edit tool usage."""

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

        formatted = f"[bold yellow]✏️[/bold yellow] [bold cyan]Edit[/bold cyan]([yellow]{filename}[/yellow])"

        # Show line count change
        if len(old_lines) == len(new_lines):
            formatted += f" [dim]({len(old_lines)} lines modified)[/dim]"
        else:
            diff = len(new_lines) - len(old_lines)
            if diff > 0:
                formatted += f" [dim](+{diff} lines)[/dim]"
            else:
                formatted += f" [dim]({diff} lines)[/dim]"

        # Handle success check for both formats
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and "updated" in str(result_text).lower():
            formatted += " [green]✓[/green]"

        # Try to parse structured patch from tool result if available
        if tool_result:
            # Debug: show what we have
            # print(f"DEBUG EditFormatter tool_result type: {type(tool_result)}")
            # if isinstance(tool_result, dict):
            #     print(f"DEBUG EditFormatter tool_result keys: {tool_result.keys()}")

            # Handle both old string format and new structured format
            if isinstance(tool_result, dict) and "structured_data" in tool_result:
                structured_data = tool_result["structured_data"]
                if "structuredPatch" in structured_data:
                    patch_info = structured_data["structuredPatch"]
                    formatted += self._format_structured_patch(patch_info)
                else:
                    # Fall back to simple diff display
                    formatted += self._format_simple_diff(old_lines, new_lines)
            elif isinstance(tool_result, str) and "structuredPatch" in tool_result:
                try:
                    import json

                    result_data = json.loads(tool_result)
                    if "structuredPatch" in result_data:
                        patch_info = result_data["structuredPatch"]
                        formatted += self._format_structured_patch(patch_info)
                except (json.JSONDecodeError, KeyError):
                    # Fall back to simple diff display
                    formatted += self._format_simple_diff(old_lines, new_lines)
            else:
                # Fall back to simple diff display
                formatted += self._format_simple_diff(old_lines, new_lines)

        return formatted

    def _format_structured_patch(self, patch_info: list) -> str:
        """Format structured patch information like Claude Code does."""
        if not patch_info:
            return ""

        result = ""
        for patch in patch_info[:1]:  # Show only first patch to keep it compact
            lines = patch.get("lines", [])
            if lines:
                result += "\n"
                for line in lines[:5]:  # Show max 5 lines
                    if line.startswith("-"):
                        result += f"  [dim]⎿[/dim]  [red]{line}[/red]\n"
                    elif line.startswith("+"):
                        result += f"  [dim]⎿[/dim]  [green]{line}[/green]\n"
                    else:
                        result += f"  [dim]⎿[/dim]  [dim]{line}[/dim]\n"

                if len(lines) > 5:
                    additions = sum(1 for line in lines if line.startswith("+"))
                    deletions = sum(1 for line in lines if line.startswith("-"))
                    result += f"     [dim]… +{additions} -{deletions} more changes[/dim]"

        return result.rstrip()

    def _format_simple_diff(self, old_lines: list, new_lines: list) -> str:
        """Format a simple diff view when structured patch isn't available."""
        result = ""

        # Show a preview of removed lines (up to 3)
        removed_count = 0
        for line in old_lines[:3]:
            if line.strip():
                display_line = line[:60] + "..." if len(line) > 60 else line
                result += f"\n  [dim]⎿[/dim]  [red]- {display_line}[/red]"
                removed_count += 1

        # Show a preview of added lines (up to 3)
        added_count = 0
        for line in new_lines[:3]:
            if line.strip():
                display_line = line[:60] + "..." if len(line) > 60 else line
                result += f"\n  [dim]⎿[/dim]  [green]+ {display_line}[/green]"
                added_count += 1

        # Show summary if there are more changes
        total_removed = len([line for line in old_lines if line.strip()])
        total_added = len([line for line in new_lines if line.strip()])

        if total_removed > removed_count or total_added > added_count:
            more_removed = total_removed - removed_count
            more_added = total_added - added_count
            if more_removed > 0 or more_added > 0:
                result += f"\n     [dim]… +{more_added} -{more_removed} more changes[/dim]"

        return result


class MultiEditFormatter(ToolFormatter):
    """Format MultiEdit tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format multi-edit operation."""
        input_data = tool_use.get("input", {})
        file_path = input_data.get("file_path", "unknown file")
        edits = input_data.get("edits", [])

        filename = Path(file_path).name
        edit_count = len(edits)

        formatted = f"[bold yellow]✏️[/bold yellow] [bold cyan]MultiEdit[/bold cyan]([yellow]{filename}[/yellow])"
        formatted += f" [dim]({edit_count} edits)[/dim]"

        if tool_result:
            # Handle success check for both formats
            result_text = tool_result
            if isinstance(tool_result, dict) and "text" in tool_result:
                result_text = tool_result["text"]

            if "Applied" in result_text and "edits" in result_text:
                formatted += " [green]✓[/green]"

            # Try to parse structured patch from tool result if available
            if isinstance(tool_result, dict) and "structured_data" in tool_result:
                structured_data = tool_result["structured_data"]
                if "structuredPatch" in structured_data:
                    patch_info = structured_data["structuredPatch"]
                    formatted += self._format_structured_patch(patch_info)
            elif isinstance(tool_result, str) and "structuredPatch" in tool_result:
                try:
                    import json

                    result_data = json.loads(tool_result)
                    if "structuredPatch" in result_data:
                        patch_info = result_data["structuredPatch"]
                        formatted += self._format_structured_patch(patch_info)
                except (json.JSONDecodeError, KeyError):
                    pass

        return formatted

    def _format_structured_patch(self, patch_info: list) -> str:
        """Format structured patch information like Claude Code does."""
        if not patch_info:
            return ""

        result = ""
        total_additions = 0
        total_deletions = 0

        # Count total changes across all patches
        for patch in patch_info:
            lines = patch.get("lines", [])
            total_additions += sum(1 for line in lines if line.startswith("+"))
            total_deletions += sum(1 for line in lines if line.startswith("-"))

        # Show first few changes
        first_patch = patch_info[0] if patch_info else {}
        lines = first_patch.get("lines", [])
        if lines:
            result += "\n"
            for line in lines[:3]:  # Show max 3 lines to keep compact
                if line.startswith("-"):
                    result += f"  [dim]⎿[/dim]  [red]{line}[/red]\n"
                elif line.startswith("+"):
                    result += f"  [dim]⎿[/dim]  [green]{line}[/green]\n"
                else:
                    result += f"  [dim]⎿[/dim]  [dim]{line}[/dim]\n"

            if len(patch_info) > 1 or len(lines) > 3:
                result += f"     [dim]… +{total_additions} -{total_deletions} total changes[/dim]"

        return result.rstrip()


class TaskFormatter(ToolFormatter):
    """Format Task tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format task delegation."""
        input_data = tool_use.get("input", {})
        description = input_data.get("description", "Task")

        formatted = f"[bold magenta]🤖[/bold magenta] [bold cyan]Task[/bold cyan]: {description}"

        if tool_result:
            # Handle both string and dict formats for tool_result
            result_text = tool_result
            if isinstance(tool_result, dict) and "text" in tool_result:
                result_text = tool_result["text"]

            # Show summary of task result
            lines = str(result_text).strip().split("\n")
            if lines:
                summary = lines[0][:100]
                if len(lines[0]) > 100 or len(lines) > 1:
                    summary += "..."
                formatted += f"\n  [dim]→[/dim] {summary}"

        return formatted


class GrepFormatter(ToolFormatter):
    """Format Grep tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format grep search."""
        input_data = tool_use.get("input", {})
        pattern = input_data.get("pattern", "")
        path = input_data.get("path", ".")

        formatted = f"[bold cyan]🔍[/bold cyan] [bold cyan]Grep[/bold cyan]([yellow]{pattern}[/yellow])"

        if path != ".":
            formatted += f" in {Path(path).name}"

        if tool_result:
            # Handle both string and dict formats for tool_result
            result_text = tool_result
            if isinstance(tool_result, dict) and "text" in tool_result:
                result_text = tool_result["text"]

            matches = str(result_text).strip().split("\n")
            match_count = len([m for m in matches if m])
            if match_count > 0:
                formatted += f" [green]({match_count} matches)[/green]"
            else:
                formatted += " [dim](no matches)[/dim]"

        return formatted


class LSFormatter(ToolFormatter):
    """Format LS tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format directory listing."""
        input_data = tool_use.get("input", {})
        path = input_data.get("path", "")

        dirname = Path(path).name or path
        formatted = f"[bold blue]📁[/bold blue] [bold cyan]LS[/bold cyan]([yellow]{dirname}/[/yellow])"

        # Handle both string and dict formats for tool_result
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and str(result_text).strip():
            lines = str(result_text).strip().split("\n")
            # Filter out system messages and extract just the file listing
            clean_lines = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith("NOTE:") and "-" in line:
                    clean_lines.append(line)

            if clean_lines and len(clean_lines) <= 5:
                # Show files inline if short list
                for line in clean_lines[:3]:
                    formatted += f"\n  [dim]⎿[/dim]  {line}"
                if len(clean_lines) > 3:
                    formatted += f"\n\n     [dim]… +{len(clean_lines) - 3} files[/dim]"
            elif clean_lines:
                formatted += f" [dim]({len(clean_lines)} items)[/dim]"

        return formatted


class TodoReadFormatter(ToolFormatter):
    """Format TodoRead tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format todo list reading."""
        formatted = "[bold green]⏺[/bold green] [bold cyan]Read Todos[/bold cyan]"

        # Handle both string and dict formats for tool_result
        result_text = tool_result
        if isinstance(tool_result, dict) and "text" in tool_result:
            result_text = tool_result["text"]

        if result_text and "todo" in str(result_text).lower():
            # Try to parse and show todos from the result
            lines = str(result_text).strip().split("\n")
            todo_count = 0
            for line in lines:
                if any(marker in line for marker in ["pending", "in_progress", "completed", "☐", "☒"]):
                    todo_count += 1

            if todo_count > 0:
                formatted += f" [dim]({todo_count} todos)[/dim]"

        return formatted


class TodoWriteFormatter(ToolFormatter):
    """Format TodoWrite tool usage."""

    def format(self, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format todo list updates."""
        input_data = tool_use.get("input", {})
        todos = input_data.get("todos", [])

        formatted = "[bold green]⏺[/bold green] [bold cyan]Update Todos[/bold cyan]"

        if todos:
            # Show up to 5 todos
            for i, todo in enumerate(todos[:5]):
                content = todo.get("content", "")
                status = todo.get("status", "pending")

                # Choose checkbox and formatting based on status
                if status == "completed":
                    checkbox = "[green]☒[/green]"
                    # Add strikethrough for completed todos
                    content_formatted = f"[strikethrough dim]{content}[/strikethrough dim]"
                elif status == "in_progress":
                    checkbox = "☐"  # or could use ◯
                    content_formatted = content
                else:  # pending
                    checkbox = "☐"
                    content_formatted = content

                # Truncate long content (after applying formatting)
                if len(content) > 60:
                    if status == "completed":
                        truncated = content[:57] + "..."
                        content_formatted = f"[strikethrough dim]{truncated}[/strikethrough dim]"
                    else:
                        content_formatted = content[:57] + "..."

                # First item uses ⎿, others use spaces for alignment
                if i == 0:
                    formatted += f"\n  [dim]⎿[/dim]  {checkbox} {content_formatted}"
                else:
                    formatted += f"\n     {checkbox} {content_formatted}"

            # If there are more todos, indicate that
            if len(todos) > 5:
                formatted += f"\n     [dim]… +{len(todos) - 5} more todos[/dim]"

        return formatted


# Registry of tool formatters
TOOL_FORMATTERS = {
    "Bash": BashFormatter(),
    "Read": ReadFormatter(),
    "Write": WriteFormatter(),
    "Edit": EditFormatter(),
    "MultiEdit": MultiEditFormatter(),
    "Task": TaskFormatter(),
    "Grep": GrepFormatter(),
    "LS": LSFormatter(),
    "TodoRead": TodoReadFormatter(),
    "TodoWrite": TodoWriteFormatter(),
}


def format_tool_use(tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
    """Format a tool use with the appropriate formatter."""
    formatter = TOOL_FORMATTERS.get(tool_name)

    if formatter:
        return formatter.format(tool_use, tool_result)
    else:
        # Fallback for unknown tools
        return f"[bold cyan]🔧 {tool_name}[/bold cyan]"
