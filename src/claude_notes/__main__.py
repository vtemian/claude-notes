"""Entry point for the claude-notes CLI."""

import os
import sys

from claude_notes.cli import cli


def main():
    """Main entry point."""
    # Fix Windows console encoding issues
    if sys.platform == "win32":
        # Try to set UTF-8 encoding for stdout/stderr
        try:
            if sys.stdout.encoding.lower() != "utf-8":
                sys.stdout.reconfigure(encoding="utf-8")
            if sys.stderr.encoding.lower() != "utf-8":
                sys.stderr.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            # Fallback: set environment variable
            os.environ.setdefault("PYTHONIOENCODING", "utf-8")

    cli()


if __name__ == "__main__":
    main()
