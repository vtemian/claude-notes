"""CLI commands for claude-notes."""

from datetime import datetime, timezone
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from claude_notes.parser import TranscriptParser

console = Console()


def get_claude_projects_dir() -> Path:
    """Get the Claude projects directory."""
    return Path.home() / ".claude" / "projects"


def decode_project_path(encoded_name: str) -> str:
    """Decode the project folder name to actual path."""
    # Remove leading dash and replace dashes with slashes
    if encoded_name.startswith("-"):
        encoded_name = encoded_name[1:]

    return "/" + encoded_name.replace("-", "/")


def list_projects() -> list[tuple[str, Path, int]]:
    """List all Claude projects with their paths and transcript counts."""
    projects_dir = get_claude_projects_dir()

    if not projects_dir.exists():
        return []

    projects = []

    for project_folder in projects_dir.iterdir():
        if project_folder.is_dir() and project_folder.name.startswith("-"):
            # Decode the project path
            actual_path = decode_project_path(project_folder.name)

            # Count JSONL files (transcripts)
            jsonl_files = list(project_folder.glob("*.jsonl"))
            transcript_count = len(jsonl_files)

            projects.append((actual_path, project_folder, transcript_count))

    # Sort by path
    projects.sort(key=lambda x: x[0])

    return projects


@click.group()
@click.version_option()
def cli():
    """Transform Claude Code transcript JSONL files to readable formats."""
    pass


@cli.command(name="list-projects")
def list_projects_cmd():
    """List all Claude projects."""
    projects = list_projects()

    if not projects:
        console.print("[yellow]No Claude projects found in ~/.claude/projects/[/yellow]")
        return

    # Create a rich table
    table = Table(title="Claude Projects")
    table.add_column("Project Path", style="cyan")
    table.add_column("Transcripts", justify="right", style="green")
    table.add_column("Folder Name", style="dim")

    for project_path, project_folder, transcript_count in projects:
        table.add_row(project_path, str(transcript_count), project_folder.name)

    console.print(table)
    console.print(f"\n[dim]Total projects: {len(projects)}[/dim]")


def encode_project_path(path: str) -> str:
    """Encode a project path to Claude folder name format."""
    # Remove leading slash and replace slashes with dashes
    if path.startswith("/"):
        path = path[1:]
    return "-" + path.replace("/", "-")


def find_project_folder(project_path: Path) -> Path | None:
    """Find the Claude project folder for a given project path."""
    projects_dir = get_claude_projects_dir()
    encoded_name = encode_project_path(str(project_path))
    project_folder = projects_dir / encoded_name

    if project_folder.exists() and project_folder.is_dir():
        return project_folder
    return None


def parse_start_time(time_str: str) -> datetime | None:
    """Parse ISO format datetime string and convert to UTC."""
    if not time_str:
        return None

    try:
        # Parse the ISO format datetime
        dt = datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        # Convert to UTC if it has timezone info
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--raw", is_flag=True, help="Show raw JSON data instead of formatted view")
@click.option("--no-pager", is_flag=True, help="Disable pager and show all content at once")
@click.option("--format", type=click.Choice(["terminal", "html"]), default="terminal", help="Output format")
@click.option("--output", type=click.Path(), help="Output file for HTML format")
def show(path: Path, raw: bool, no_pager: bool, format: str, output: str | None):
    """Show all conversations for a Claude project.

    If PATH is not specified, uses the current directory.
    """
    # Convert to absolute path
    abs_path = path.resolve()

    # Find the project folder
    project_folder = find_project_folder(abs_path)

    if not project_folder:
        console.print(f"[red]Error:[/red] No Claude project found for path: {abs_path}")
        console.print("\n[dim]Hint: Use 'claude-notes list-projects' to see all available projects[/dim]")
        return

    # List all JSONL files
    jsonl_files = sorted(project_folder.glob("*.jsonl"))

    if not jsonl_files:
        console.print(f"[yellow]No transcript files found in project: {abs_path}[/yellow]")
        return

    # No header output - just start with the conversation

    # Load all conversations
    conversations = []
    for jsonl_file in jsonl_files:
        try:
            parser = TranscriptParser(jsonl_file)
            info = parser.get_conversation_info()
            messages = parser.get_messages()

            # Get the start timestamp for sorting (convert to UTC)
            start_time = parse_start_time(info.get("start_time", ""))

            # Get file modification time as fallback (in UTC)
            file_mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime, tz=timezone.utc)

            conversations.append(
                {
                    "file": jsonl_file,
                    "info": info,
                    "messages": messages,
                    "start_time": start_time,
                    "file_mtime": file_mtime,
                }
            )
        except Exception as e:
            console.print(f"[red]Error parsing {jsonl_file.name}: {e}[/red]")

    # Sort conversations by start time (newest first), with file modification time as fallback
    # Use timezone-aware datetime.min to avoid comparison issues
    conversations.sort(
        key=lambda x: x["start_time"] or x["file_mtime"] or datetime.min.replace(tzinfo=timezone.utc), reverse=True
    )

    if raw:
        # Display raw JSON data
        import json

        for conv in conversations:
            console.print(f"\n[bold cyan]Conversation: {conv['info'].get('conversation_id', 'Unknown')}[/bold cyan]")
            console.print(json.dumps(conv["messages"], indent=2))
    elif format == "html":
        # Generate HTML output
        from claude_notes.formatters.factory import FormatterFactory
        from claude_notes.formatters.html import get_html_css

        formatter = FormatterFactory.create_formatter("html")

        # Collect all formatted content
        html_parts = []
        html_parts.append("<!DOCTYPE html>")
        html_parts.append('<html lang="en">')
        html_parts.append("<head>")
        html_parts.append('<meta charset="UTF-8">')
        html_parts.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
        html_parts.append("<title>Claude Conversations</title>")
        html_parts.append(get_html_css())
        html_parts.append("</head>")
        html_parts.append("<body>")
        html_parts.append('<div class="container">')

        # Add conversation navigation if multiple conversations
        if len(conversations) > 1:
            html_parts.append('<div class="conversation-nav">')
            html_parts.append("<h2>Conversations</h2>")
            html_parts.append('<ul class="conversation-toc">')
            for i, conv in enumerate(conversations):
                conv_id = conv["info"].get("conversation_id", f"conv-{i+1}")
                start_time = conv["info"].get("start_time", "Unknown time")
                html_parts.append(f'<li><a href="#conv-{conv_id}">📝 Conversation {i+1} ({start_time})</a></li>')
            html_parts.append("</ul>")
            html_parts.append("</div>")

        for i, conv in enumerate(conversations):
            # Reverse the messages so newest appears first
            reversed_messages = list(reversed(conv["messages"]))
            html_content = formatter.format_conversation(reversed_messages, conv["info"])
            html_parts.append(html_content)
            if i < len(conversations) - 1:
                html_parts.append('<hr style="margin: 40px 0; border: 1px solid #e1e5e9;">')

        # Add back to top link
        html_parts.append('<div class="back-to-top">')
        html_parts.append('<a href="#top">⬆️ Back to Top</a>')
        html_parts.append("</div>")

        html_parts.append("</div>")
        html_parts.append("</body>")
        html_parts.append("</html>")

        html_output = "\n".join(html_parts)

        if output:
            # Write to file
            output_path = Path(output)
            output_path.write_text(html_output, encoding="utf-8")
            console.print(f"[green]HTML output written to: {output_path}[/green]")
        else:
            # Print to stdout
            print(html_output)
    else:
        # Display formatted conversations in terminal
        from claude_notes.formatters.terminal import TerminalFormatter

        formatter = TerminalFormatter(console)

        if no_pager:
            # Display all content at once without pager
            for _i, conv in enumerate(conversations):
                # Reverse the messages so newest appears first
                reversed_messages = list(reversed(conv["messages"]))
                formatter.display_conversation(reversed_messages, conv["info"])
        else:
            # Use pager for progressive display
            from claude_notes.pager import Pager

            pager = Pager(console)

            # Collect all formatted content first
            for _i, conv in enumerate(conversations):
                # Reverse the messages so newest appears first
                reversed_messages = list(reversed(conv["messages"]))
                pager.add_conversation(reversed_messages, conv["info"], formatter)

            # Start the pager interface
            pager.display()
