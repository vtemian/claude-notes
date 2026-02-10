"""CLI commands for claude-notes."""
# ruff: noqa: UP017  # Use timezone.utc for Python <3.11 compatibility

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


def _decode_segments(encoded: str, separator: str) -> str:
    """Decode dash-separated segments, where '--' represents a literal dash."""
    decoded_parts: list[str] = []
    i = 0
    while i < len(encoded):
        char = encoded[i]
        if char == "-":
            if i + 1 < len(encoded) and encoded[i + 1] == "-":
                decoded_parts.append("-")
                i += 2
            else:
                decoded_parts.append(separator)
                i += 1
        else:
            decoded_parts.append(char)
            i += 1
    return "".join(decoded_parts)


def _encode_segments(path: str) -> str:
    """Encode path segments by replacing slashes with dashes."""
    return path.replace("/", "-")


def decode_project_path(encoded_name: str) -> str:
    """Decode the project folder name to actual path."""
    # Windows path (e.g., "C--Users-projects-my--project")
    if len(encoded_name) >= 3 and encoded_name[1:3] == "--" and encoded_name[0].isalpha():
        drive = encoded_name[0]
        rest_encoded = encoded_name[3:]
        rest = _decode_segments(rest_encoded, "/")
        return f"{drive}:/{rest}" if rest else f"{drive}:/"

    # Unix/Linux path (e.g., "-home-user-my--project")
    if encoded_name.startswith("-"):
        encoded_body = encoded_name[1:]
        decoded_body = _decode_segments(encoded_body, "/")
        return "/" + decoded_body

    # Fallback: return as-is if it doesn't match expected encodings
    return encoded_name


def list_projects() -> list[tuple[str, Path, int]]:
    """List all Claude projects with their paths and transcript counts."""
    projects_dir = get_claude_projects_dir()

    if not projects_dir.exists():
        return []

    projects = []

    for project_folder in projects_dir.iterdir():
        if not project_folder.is_dir():
            continue

        # Check if it's a valid project folder
        # Unix/Linux: starts with "-" (e.g., "-home-user-project")
        # Windows: starts with drive letter (e.g., "c--Users-Jack-project" or "C--Users-Jack-project")
        name = project_folder.name
        is_valid = name.startswith("-") or (len(name) >= 3 and name[1:3] == "--" and name[0].isalpha())

        if is_valid:
            # Decode the project path
            actual_path = decode_project_path(name)

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
    normalized = path.replace("\\", "/")

    # Windows path with drive letter (e.g., C:/Users/...)
    if len(normalized) >= 2 and normalized[1] == ":" and normalized[0].isalpha():
        drive = normalized[0]
        rest = normalized[2:]
        if rest.startswith("/"):
            rest = rest[1:]
        encoded_rest = _encode_segments(rest)
        return f"{drive}--{encoded_rest}"

    # Unix/Linux path (leading slash)
    normalized = normalized.lstrip("/")
    encoded_body = _encode_segments(normalized)
    return "-" + encoded_body


def find_project_folder(project_path: Path) -> Path | None:
    """Find the Claude project folder for a given project path."""
    projects_dir = get_claude_projects_dir()
    encoded_name = encode_project_path(str(project_path))
    project_folder = projects_dir / encoded_name

    # Try exact match first
    if project_folder.exists() and project_folder.is_dir():
        return project_folder

    # On Windows, try case-insensitive match (drive letter might be uppercase or lowercase)
    if not projects_dir.exists():
        return None

    encoded_lower = encoded_name.lower()
    for folder in projects_dir.iterdir():
        if folder.is_dir() and folder.name.lower() == encoded_lower:
            return folder

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


def order_messages(messages: list, message_order: str) -> list:
    """Order messages based on the specified order."""
    if message_order == "asc":
        return messages
    else:  # desc
        return list(reversed(messages))


@cli.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path), default=".")
@click.option("--raw", is_flag=True, help="Show raw JSON data instead of formatted view")
@click.option("--no-pager", is_flag=True, help="Disable pager and show all content at once")
@click.option("--format", type=click.Choice(["terminal", "html", "animated"]), default="terminal", help="Output format")
@click.option("--output", type=click.Path(), help="Output file (HTML/GIF/MP4/cast format)")
@click.option(
    "--session-order",
    type=click.Choice(["asc", "desc"]),
    default="desc",
    help="Order sessions by timestamp (asc=oldest first, desc=newest first)",
)
@click.option(
    "--message-order",
    type=click.Choice(["asc", "desc"]),
    default=None,
    help="Order messages within sessions (asc=oldest first, desc=newest first). Defaults to asc for HTML, desc for terminal.",
)
@click.option("--style", type=click.Path(exists=True), help="Custom CSS file to include with HTML format")
@click.option(
    "--typing-speed", type=float, default=0.05, help="Typing speed in seconds per character (animated format)"
)
@click.option(
    "--pause-duration", type=float, default=2.0, help="Pause duration between messages in seconds (animated format)"
)
@click.option("--cols", type=int, default=120, help="Terminal columns (animated format)")
@click.option("--rows", type=int, default=30, help="Terminal rows (animated format)")
@click.option("--max-duration", type=float, help="Maximum animation duration in seconds (animated format)")
@click.option(
    "--emoji-fallbacks",
    is_flag=True,
    help="Replace emoji with text fallbacks for better GIF compatibility (animated format)",
)
def show(
    path: Path,
    raw: bool,
    no_pager: bool,
    format: str,
    output: str | None,
    session_order: str,
    message_order: str,
    style: str | None,
    typing_speed: float,
    pause_duration: float,
    cols: int,
    rows: int,
    max_duration: float | None,
    emoji_fallbacks: bool,
):
    """Show all conversations for a Claude project.

    If PATH is not specified, uses the current directory.
    """
    # Set default message order based on format if not explicitly provided
    if message_order is None:
        message_order = "asc" if format == "html" else "desc"

    # Convert to absolute path
    abs_path = path.resolve()

    # Check if the path is a direct .jsonl file
    if abs_path.is_file() and abs_path.suffix == ".jsonl":
        # Use the file directly
        jsonl_files = [abs_path]
    else:
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

    # Sort conversations by start time, with file modification time as fallback
    # Use timezone-aware datetime.min to avoid comparison issues
    conversations.sort(
        key=lambda x: x["start_time"] or x["file_mtime"] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=(session_order == "desc"),
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
        from claude_notes.formatters.html import get_extra_html_css, get_html_css

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
        html_parts.append(get_extra_html_css(style))
        html_parts.append("</head>")
        html_parts.append('<body id="top">')
        # Theme toggle and burger menu buttons
        html_parts.append('<button class="theme-toggle" onclick="toggleTheme()">Theme</button>')
        html_parts.append('<button class="burger-menu" onclick="toggleSidebar()">Stats</button>')
        html_parts.append('<div class="sidebar-overlay" onclick="toggleSidebar()"></div>')
        html_parts.append('<div class="container">')

        # Add conversation navigation if multiple conversations
        if len(conversations) > 1:
            html_parts.append('<div class="conversation-nav">')
            html_parts.append("<h2>Conversations</h2>")
            html_parts.append('<ul class="conversation-toc">')
            for i, conv in enumerate(conversations):
                conv_id = conv["info"].get("conversation_id", f"conv-{i + 1}")
                start_time = conv["info"].get("start_time", "Unknown time")
                html_parts.append(f'<li><a href="#conv-{conv_id}">📝 Conversation {i + 1} ({start_time})</a></li>')
            html_parts.append("</ul>")
            html_parts.append("</div>")

        for i, conv in enumerate(conversations):
            # Order the messages based on user preference
            ordered_messages = order_messages(conv["messages"], message_order)
            html_content = formatter.format_conversation(ordered_messages, conv["info"])
            html_parts.append(html_content)
            if i < len(conversations) - 1:
                html_parts.append('<hr style="margin: 50px 0; border: none; border-top: 1px solid var(--border);">')

        # Add back to top link
        html_parts.append('<div class="back-to-top">')
        html_parts.append('<a href="#top">⬆️ Back to Top</a>')
        html_parts.append("</div>")

        html_parts.append("</div>")
        # Theme toggle JavaScript
        html_parts.append("""<script>
function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
}
function toggleSidebar() {
    const sidebars = document.querySelectorAll('.thread-sidebar');
    const overlay = document.querySelector('.sidebar-overlay');
    sidebars.forEach(sidebar => sidebar.classList.toggle('open'));
    if (overlay) overlay.classList.toggle('open');
}
// Load saved theme or default to dark
const savedTheme = localStorage.getItem('theme') || 'dark';
document.documentElement.setAttribute('data-theme', savedTheme);
</script>""")
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
    elif format == "animated":
        # Generate animated GIF
        from claude_notes.formatters.factory import FormatterFactory

        # Create animated formatter with options
        formatter_kwargs = {
            "typing_speed": typing_speed,
            "pause_duration": pause_duration,
            "cols": cols,
            "rows": rows,
            "max_duration": max_duration,
            "use_emoji_fallbacks": emoji_fallbacks,
        }

        try:
            formatter = FormatterFactory.create_formatter("animated", **formatter_kwargs)
        except (ImportError, RuntimeError) as e:
            console.print(f"[red]Error:[/red] {e}")
            console.print("[dim]Hint: Install animation dependencies with: uv add --optional-deps animation[/dim]")
            return

        # Collect all conversations into a single asciicast
        all_messages = []
        for conv in conversations:
            # Order the messages based on user preference
            ordered_messages = order_messages(conv["messages"], message_order)
            all_messages.extend(ordered_messages)

            # Add separator between conversations if multiple
            if len(conversations) > 1:
                separator_msg = {
                    "type": "assistant",
                    "message": {
                        "role": "assistant",
                        "content": f"\n--- Conversation {conversations.index(conv) + 1} ---\n",
                    },
                }
                all_messages.append(separator_msg)

        # Generate asciicast
        try:
            cast_file = formatter.format_conversation(all_messages, conversation_info={})

            # Handle output options
            if output:
                output_path = Path(output)
                base_name = output_path.stem
                output_dir = output_path.parent

                # Always save the cast file alongside the output
                cast_output = output_dir / f"{base_name}.cast"
                import shutil

                shutil.copy2(cast_file, cast_output)
                console.print(f"[cyan]Asciicast file saved: {cast_output}[/cyan]")

                # Generate output based on file extension
                if output.endswith(".gif") or not output_path.suffix:
                    gif_output = str(output_path.with_suffix(".gif"))
                    formatter.generate_gif(cast_file, gif_output)
                    console.print(f"[green]Animated GIF generated: {gif_output}[/green]")
                elif output.endswith(".mp4"):
                    mp4_output = str(output_path.with_suffix(".mp4"))
                    formatter.generate_mp4(cast_file, mp4_output)
                    console.print(f"[green]MP4 video generated: {mp4_output}[/green]")
                elif output.endswith(".cast"):
                    # User specifically requested just the cast file
                    console.print(f"[green]Asciicast file saved: {cast_output}[/green]")
                else:
                    # Unknown extension, assume they want GIF
                    gif_output = str(output_path.with_suffix(".gif"))
                    formatter.generate_gif(cast_file, gif_output)
                    console.print(f"[green]Animated GIF generated: {gif_output}[/green]")
            else:
                console.print(f"[yellow]Asciicast file generated: {cast_file}[/yellow]")
                console.print("[dim]Use --output filename.cast/.gif/.mp4 to save in desired format[/dim]")

        except Exception as e:
            console.print(f"[red]Error generating animation: {e}[/red]")

    else:
        # Display formatted conversations in terminal
        from claude_notes.formatters.terminal import TerminalFormatter

        formatter = TerminalFormatter(console)

        if no_pager:
            # Display all content at once without pager
            for _i, conv in enumerate(conversations):
                # Order the messages based on user preference
                ordered_messages = order_messages(conv["messages"], message_order)
                formatter.display_conversation(ordered_messages, conv["info"])
        else:
            # Use pager for progressive display
            from claude_notes.pager import Pager

            pager = Pager(console)

            # Collect all formatted content first
            for _i, conv in enumerate(conversations):
                # Order the messages based on user preference
                ordered_messages = order_messages(conv["messages"], message_order)
                pager.add_conversation(ordered_messages, conv["info"], formatter)

            # Start the pager interface
            pager.display()
