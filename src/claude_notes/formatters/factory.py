"""Factory for creating formatters based on output format."""

from rich.console import Console

from claude_notes.formatters.base import BaseFormatter, OutputFormat
from claude_notes.formatters.html import HTMLFormatter
from claude_notes.formatters.terminal import TerminalFormatter


class FormatterFactory:
    """Factory for creating appropriate formatters."""

    @staticmethod
    def create_formatter(format_type: str, console: Console | None = None, **kwargs) -> BaseFormatter:
        """Create a formatter based on the specified format type.

        Args:
            format_type: The output format (terminal, html, animated)
            console: Console instance for terminal formatters
            **kwargs: Additional arguments for specific formatters

        Returns:
            Appropriate formatter instance

        Raises:
            ValueError: If format_type is not supported
        """
        if format_type == OutputFormat.TERMINAL:
            return TerminalFormatter(console)
        elif format_type == OutputFormat.HTML:
            return HTMLFormatter()
        elif format_type == OutputFormat.ANIMATED:
            from claude_notes.formatters.animated import AnimatedFormatter

            return AnimatedFormatter(**kwargs)
        else:
            raise ValueError(f"Unsupported format type: {format_type}")

    @staticmethod
    def get_supported_formats() -> list[str]:
        """Get list of supported output formats."""
        return [OutputFormat.TERMINAL, OutputFormat.HTML, OutputFormat.ANIMATED]
