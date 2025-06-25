"""Pager implementation for progressive content display like 'less' CLI."""

import sys
import termios
import tty
from typing import Any

from rich.console import Console
from rich.text import Text

from claude_notes.formatters.terminal import TerminalFormatter


class Pager:
    """A pager that displays content progressively like the 'less' command."""

    def __init__(self, console: Console | None = None):
        """Initialize the pager.

        Args:
            console: Rich console instance
        """
        self.console = console or Console()
        self.conversations: list[dict[str, Any]] = []
        self.current_line = 0
        self.lines_per_page = self.console.size.height - 1
        self._rendered_lines: list[Any] | None = None

    def add_conversation(
        self, messages: list[dict[str, Any]], info: dict[str, Any], formatter: TerminalFormatter
    ) -> None:
        """Add a conversation to the pager content."""
        self.conversations.append({"messages": messages, "info": info})
        # Clear cached rendered lines when new content is added
        self._rendered_lines = None

    def _rebuild_content(self) -> None:
        """Rebuild content from all conversations."""
        # Don't pre-render - instead just track conversations for on-demand rendering
        # This preserves Rich formatting by rendering fresh each time
        pass

    def _get_rendered_lines(self) -> list[Any]:
        """Get all rendered lines with Rich formatting preserved."""
        if self._rendered_lines is None:
            self._rendered_lines = []

            for i, conv in enumerate(self.conversations):
                if i > 0:
                    # Add separator between conversations
                    self._rendered_lines.append(Text(""))

                # Create a console that outputs ANSI codes
                from io import StringIO

                from rich.console import Console

                temp_output = StringIO()
                temp_console = Console(file=temp_output, width=self.console.size.width, force_terminal=True)

                # Format conversation
                temp_formatter = TerminalFormatter(temp_console)
                temp_formatter.display_conversation(conv["messages"], conv["info"])

                # Get content and split by lines
                content = temp_output.getvalue()
                lines = content.split("\n")

                for line in lines:
                    # Use Text.from_ansi to convert ANSI codes back to Rich formatting
                    rich_line = Text.from_ansi(line)
                    self._rendered_lines.append(rich_line)

        return self._rendered_lines

    def display(self) -> None:
        """Display content with pager controls."""
        if not self.conversations:
            self.console.print("[dim]No content to display[/dim]")
            return

        # Update lines per page based on current terminal size
        self.lines_per_page = self.console.size.height - 1

        # Start from the top (0%) like normal 'less' behavior
        self.current_line = 0

        try:
            while True:
                self._display_page()

                rendered_lines = self._get_rendered_lines()
                if self.current_line >= len(rendered_lines):
                    # Reached end of content - show END status and wait for quit
                    self._show_end_status()
                    action = self._get_user_input()
                    if action == "quit":
                        self.console.clear()
                        break
                    elif action == "prev_page":
                        self.current_line = max(0, self.current_line - self.lines_per_page)
                        continue
                    elif action == "top":
                        self.current_line = 0
                        continue
                    else:
                        break

                # Show status and wait for user input
                self._show_status()
                action = self._get_user_input()

                if action == "quit":
                    self.console.clear()
                    break
                elif action == "next_page":
                    rendered_lines = self._get_rendered_lines()
                    self.current_line = min(len(rendered_lines), self.current_line + self.lines_per_page)
                elif action == "next_line":
                    rendered_lines = self._get_rendered_lines()
                    self.current_line = min(len(rendered_lines), self.current_line + 1)
                elif action == "prev_page":
                    self.current_line = max(0, self.current_line - self.lines_per_page)
                elif action == "prev_line":
                    self.current_line = max(0, self.current_line - 1)
                elif action == "top":
                    self.current_line = 0
                elif action == "bottom":
                    rendered_lines = self._get_rendered_lines()
                    self.current_line = max(0, len(rendered_lines) - self.lines_per_page)
                elif action == "help":
                    # Help was already shown, just continue
                    continue

        except KeyboardInterrupt:
            self.console.clear()
            self.console.print("[dim]Interrupted[/dim]")

    def _display_page(self) -> None:
        """Display the current page of content."""
        # Clear screen completely before displaying new page
        self.console.clear()

        rendered_lines = self._get_rendered_lines()

        # Calculate which lines to show
        start_line = self.current_line
        end_line = min(len(rendered_lines), start_line + self.lines_per_page)

        # Display the lines for this page
        for i in range(start_line, end_line):
            if i < len(rendered_lines):
                # Print the Rich Text object (preserves formatting)
                self.console.print(rendered_lines[i])

    def _show_status(self) -> None:
        """Show pager status line."""
        rendered_lines = self._get_rendered_lines()
        total_lines = len(rendered_lines)

        # Calculate percentage through content
        if total_lines > 0:
            percentage = min(100, int((self.current_line + self.lines_per_page) * 100 / total_lines))
        else:
            percentage = 100

        # Show line position and percentage
        line_info = f"lines {self.current_line + 1}-{min(total_lines, self.current_line + self.lines_per_page)} of {total_lines} ({percentage}%)"

        status = f"[dim]:[/dim] {line_info} [dim](press q to quit, h for help)[/dim]"
        self.console.print(status, end="")

    def _show_end_status(self) -> None:
        """Show end-of-content status line."""
        status = "[dim]:[/dim] [bold](END)[/bold] [dim]-- press 'q' to quit, 'b' for previous page --[/dim]"
        self.console.print(status, end="")

    def _get_user_input(self) -> str:
        """Get user input for pager controls."""
        try:
            # Save terminal settings
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            # Set terminal to raw mode for single character input
            tty.setraw(sys.stdin.fileno())

            # Read single character
            ch = sys.stdin.read(1)

            # Restore terminal settings
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

            # Handle different key presses
            if ch == "\n" or ch == "\r" or ch == " ":  # Enter or Space
                return "next_page"
            elif ch.lower() == "q":
                return "quit"
            elif ch.lower() == "j":  # j for next line
                return "next_line"
            elif ch.lower() == "k":  # k for previous line
                return "prev_line"
            elif ch.lower() == "b":  # Back one page
                return "prev_page"
            elif ch.lower() == "g":  # Go to top
                return "top"
            elif ch.lower() == "G":  # Go to bottom
                return "bottom"
            elif ch.lower() == "h":  # Help
                self._show_help()
                return "help"
            else:
                # Default to next page for any other key
                return "next_page"

        except (termios.error, OSError):
            # Fallback for environments that don't support raw input
            try:
                line = input()
                if line.lower().startswith("q"):
                    return "quit"
                return "next_page"
            except (EOFError, KeyboardInterrupt):
                return "quit"

    def _show_help(self) -> None:
        """Show help message."""
        help_text = [
            "",
            "[bold]Pager Controls (like 'less'):[/bold]",
            "  [cyan]ENTER/SPACE[/cyan] - Next page (forward)",
            "  [cyan]j/↓[/cyan]         - Next line (down)",
            "  [cyan]k/↑[/cyan]         - Previous line (up)",
            "  [cyan]b/PageUp[/cyan]   - Previous page (back)",
            "  [cyan]g[/cyan]           - Go to top (newest messages)",
            "  [cyan]G[/cyan]           - Go to bottom (oldest messages)",
            "  [cyan]h/?[/cyan]         - Show this help",
            "  [cyan]q[/cyan]           - Quit",
            "",
            "[dim]Press any key to continue...[/dim]",
        ]

        for line in help_text:
            self.console.print(line)

        # Wait for key press
        self._get_user_input()

        # Clear help text and redisplay current page
        self.console.clear()
        # Don't call _display_page here as it will clear again, just continue with the main loop
