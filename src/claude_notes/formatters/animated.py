"""Animated GIF formatter for Claude conversations using asciinema."""

import json
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from claude_notes.formatters.base import BaseFormatter
from claude_notes.formatters.tools import format_tool_use


# Emoji fallback mappings for GIF export (since emoji don't render well in many terminal fonts)
EMOJI_FALLBACKS = {
    "🤖": "[Bot]",
    "👤": "[User]",
    "🔧": "[Tool]",
    "✓": "[OK]",
    "❌": "[X]",
    "⏰": "[Time]",
    "📊": "[Chart]",
    "🎯": "[Target]",
    "🎬": "[Video]",
    "🎨": "[Art]",
    "💡": "[Idea]",
    "⏱️": "[Timer]",
    "📁": "[Folder]",
    "📄": "[File]",
    "🔍": "[Search]",
    "🚀": "[Rocket]",
    "⚡": "[Flash]",
    "🔥": "[Fire]",
    "💻": "[Computer]",
    "🐛": "[Bug]",
    "✨": "[Sparkle]",
    "🎉": "[Party]",
    "⚠️": "[Warning]",
    "ℹ️": "[Info]",
    "🔒": "[Lock]",
    "🔓": "[Unlock]",
    "📝": "[Note]",
    "📋": "[Clipboard]",
    "🗂️": "[Files]",
    "💾": "[Save]",
    "🔄": "[Refresh]",
    "⬆️": "[Up]",
    "⬇️": "[Down]",
    "➡️": "[Right]",
    "⬅️": "[Left]",
    "🟢": "[Green]",
    "🔴": "[Red]",
    "🟡": "[Yellow]",
    "🔵": "[Blue]",
    "⚪": "[White]",
    "⚫": "[Black]",
}


class AnimatedFormatter(BaseFormatter):
    """Format Claude conversations as animated GIFs via asciinema."""

    def __init__(
        self,
        typing_speed: float = 0.05,
        pause_duration: float = 2.0,
        cols: int = 120,
        rows: int = 30,
        max_duration: float | None = None,
        use_emoji_fallbacks: bool = True,
    ):
        """Initialize the animated formatter.

        Args:
            typing_speed: Seconds per character when typing
            pause_duration: Seconds to pause between messages
            cols: Terminal columns
            rows: Terminal rows
            max_duration: Maximum duration in seconds (None for unlimited)
            use_emoji_fallbacks: Replace emoji with text fallbacks for GIF compatibility
        """
        super().__init__()
        self.typing_speed = typing_speed
        self.pause_duration = pause_duration
        self.cols = cols
        self.rows = rows
        self.max_duration = max_duration
        self.use_emoji_fallbacks = use_emoji_fallbacks
        self._check_dependencies()

    def _check_dependencies(self) -> None:
        """Check if required tools are available."""
        try:
            import asciinema  # noqa: F401
        except ImportError as err:
            raise ImportError(
                "asciinema is required for animated output. Install with: uv add --optional-deps animation"
            ) from err

        if not shutil.which("agg"):
            raise RuntimeError("agg is required for GIF conversion. Install from: https://github.com/asciinema/agg")

    def format_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> str:
        """Format and return conversation as an asciicast file path.

        Returns:
            Path to the generated asciicast file
        """
        # Create temporary file for asciicast
        temp_dir = tempfile.mkdtemp()
        cast_file = Path(temp_dir) / "conversation.cast"

        # Generate asciicast content
        cast_data = self._generate_asciicast(messages, conversation_info)

        # Write asciicast file
        with open(cast_file, "w") as f:
            for event in cast_data:
                f.write(json.dumps(event) + "\n")

        return str(cast_file)

    def format_tool_use(self, tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use with the appropriate formatter."""
        return format_tool_use(tool_name, tool_use, tool_result)

    def generate_gif(self, cast_file: str, output_path: str) -> None:
        """Convert asciicast file to GIF using agg.

        Args:
            cast_file: Path to asciicast file
            output_path: Output GIF file path
        """
        cmd = ["agg", "--cols", str(self.cols), "--rows", str(self.rows), cast_file, output_path]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"GIF conversion failed: {result.stderr}")

    def generate_mp4(self, cast_file: str, output_path: str, show_progress: bool = True) -> None:
        """Convert asciicast file to MP4 using available tools.

        Args:
            cast_file: Path to asciicast file
            output_path: Output MP4 file path
            show_progress: Whether to show conversion progress
        """
        # Method 1: Try svg-term-cli + ffmpeg (higher quality)
        if self._try_svg_term_method(cast_file, output_path, show_progress):
            return

        # Method 2: Try agg + ffmpeg (convert GIF to MP4)
        if self._try_agg_ffmpeg_method(cast_file, output_path, show_progress):
            return

        raise RuntimeError(
            "MP4 conversion failed. Install svg-term-cli (npm install -g svg-term-cli) "
            "or ensure agg and ffmpeg are available."
        )

    def _try_svg_term_method(self, cast_file: str, output_path: str, show_progress: bool = True) -> bool:
        """Try converting via svg-term-cli + ffmpeg."""
        if not shutil.which("svg-term") or not shutil.which("ffmpeg"):
            return False

        try:
            # Generate SVG with font family that supports emoji
            svg_file = cast_file.replace(".cast", ".svg")
            cmd = [
                "svg-term",
                "--in",
                cast_file,
                "--out",
                svg_file,
                "--width",
                str(self.cols),
                "--height",
                str(self.rows),
                "--font-family",
                "SF Mono, Monaco, Consolas, Liberation Mono, Courier New, Apple Color Emoji, Segoe UI Emoji",
            ]

            if show_progress:
                print(f"🔧 Converting to SVG: {' '.join(cmd)}")

            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                if show_progress:
                    print(f"❌ SVG conversion failed: {result.stderr}")
                return False

            if show_progress:
                print("✅ SVG generated successfully")

            # Convert SVG to MP4 using ffmpeg
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                svg_file,
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-vf",
                "scale=trunc(iw/2)*2:trunc(ih/2)*2",  # Ensure even dimensions
                output_path,
            ]

            if show_progress:
                print(f"🎬 Converting to MP4: {' '.join(cmd)}")

            # Run ffmpeg with progress output
            if show_progress:
                result = self._run_ffmpeg_with_progress(cmd)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up SVG file
            Path(svg_file).unlink(missing_ok=True)

            success = result.returncode == 0
            if show_progress:
                if success:
                    print("✅ MP4 conversion completed!")
                else:
                    print(f"❌ MP4 conversion failed: {result.stderr}")

            return success

        except Exception as e:
            if show_progress:
                print(f"❌ SVG method failed: {e}")
            return False

    def _try_agg_ffmpeg_method(self, cast_file: str, output_path: str, show_progress: bool = True) -> bool:
        """Try converting via agg (GIF) + ffmpeg."""
        if not shutil.which("agg") or not shutil.which("ffmpeg"):
            return False

        try:
            # Generate GIF first
            gif_file = cast_file.replace(".cast", ".gif")

            if show_progress:
                print("🎨 Generating GIF first...")

            self.generate_gif(cast_file, gif_file)

            if show_progress:
                print("✅ GIF generated successfully")

            # Convert GIF to MP4
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                gif_file,
                "-pix_fmt",
                "yuv420p",
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-vf",
                "fps=10,scale=trunc(iw/2)*2:trunc(ih/2)*2",  # Ensure even dimensions and limit fps
                output_path,
            ]

            if show_progress:
                print(f"🎬 Converting GIF to MP4: {' '.join(cmd)}")

            # Run ffmpeg with progress output
            if show_progress:
                result = self._run_ffmpeg_with_progress(cmd)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True)

            # Clean up GIF file
            Path(gif_file).unlink(missing_ok=True)

            success = result.returncode == 0
            if show_progress:
                if success:
                    print("✅ MP4 conversion completed!")
                else:
                    print("❌ MP4 conversion failed.")
                    # Check for common encoding issues
                    if "height not divisible by 2" in result.stderr or "width not divisible by 2" in result.stderr:
                        print("💡 This was likely due to odd video dimensions. The video filter should fix this.")
                    elif "libx264" in result.stderr and "Error while opening encoder" in result.stderr:
                        print("💡 Try installing a different version of ffmpeg or check codec availability.")
                    print(f"   Full error: {result.stderr[-200:]}")  # Show last 200 chars of error

            return success

        except Exception as e:
            if show_progress:
                print(f"❌ GIF+ffmpeg method failed: {e}")
            return False

    def _run_ffmpeg_with_progress(self, cmd: list[str]) -> subprocess.CompletedProcess:
        """Run ffmpeg command with progress output."""

        # Add progress output to ffmpeg command
        progress_cmd = cmd.copy()
        # Insert progress option before output file
        progress_cmd.insert(-1, "-progress")
        progress_cmd.insert(-1, "pipe:1")

        print("📊 Processing...")

        # Run the process
        process = subprocess.Popen(
            progress_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True
        )

        last_time = None

        # Monitor progress output
        for line in iter(process.stdout.readline, ""):
            line = line.strip()

            # Look for time progress
            if line.startswith("out_time_ms="):
                try:
                    time_ms = int(line.split("=")[1])
                    time_sec = time_ms / 1000000  # Convert microseconds to seconds

                    # Only update every second to avoid spam
                    if last_time is None or time_sec - last_time >= 1:
                        print(f"⏱️  Processing: {time_sec:.1f}s", end="\r", flush=True)
                        last_time = time_sec

                except (ValueError, IndexError):
                    pass

            # Look for completion
            elif line.startswith("progress="):
                status = line.split("=")[1]
                if status == "end":
                    print("\n🎯 Encoding complete")
                    break

        # Wait for process to complete
        stdout, stderr = process.communicate()

        # Return a result object similar to subprocess.run
        return subprocess.CompletedProcess(progress_cmd, process.returncode, stdout, stderr)

    def _generate_asciicast(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> list[dict]:
        """Generate asciicast events from conversation messages."""
        events = []
        current_time = 0.0

        # Header event
        header = {
            "version": 2,
            "width": self.cols,
            "height": self.rows,
            "timestamp": int(time.time()),
            "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color", "LANG": "en_US.UTF-8", "LC_ALL": "en_US.UTF-8"},
        }
        events.append(header)

        # Clear screen
        events.append([current_time, "o", "\033[2J\033[H"])
        current_time += 0.1

        # Collect tool results
        self._collect_tool_results(messages)

        # Group messages by role continuity
        grouped_messages = self._group_messages(messages)

        # Process each message group
        for group in grouped_messages:
            # Check if we've exceeded the time limit
            if self.max_duration and current_time >= self.max_duration:
                # Add a truncation message
                truncate_msg = f"\r\n\r\n⏰ [Truncated at {self.max_duration:.1f}s limit]"
                for char in truncate_msg:
                    events.append([current_time, "o", char])
                    current_time += self.typing_speed
                break

            # No extra spacing between groups - the role indicator already adds one line

            current_time = self._add_message_group_events(events, group, current_time)

            # Pause between message groups
            current_time += self.pause_duration

        return events

    def _add_message_group_events(self, events: list, messages: list[dict[str, Any]], start_time: float) -> float:
        """Add events for a message group and return updated time."""
        if not messages:
            return start_time

        current_time = start_time

        # Get the role from the first message
        first_msg = messages[0]
        message_data = first_msg.get("message", {})
        role = message_data.get("role", "unknown")

        # Add marker for user messages to delimit where user starts typing
        if role == "user":
            events.append([current_time, "m", "User Input"])
            current_time += 0.1  # Small delay after marker

        # Process each message in the group
        message_parts = []

        for msg in messages:
            # Skip tool results (handled inline)
            if msg.get("type") == "tool_result":
                continue

            msg_content = []
            message_data = msg.get("message", {})
            content = message_data.get("content", "")

            if isinstance(content, str):
                # Parse special tags for user messages
                if role == "user":
                    content = self._parse_special_tags(content)
                msg_content.append(content)
            elif isinstance(content, list):
                # Handle content array (text + tool uses)
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text = item.get("text", "")
                            if role == "user":
                                text = self._parse_special_tags(text)
                            msg_content.append(text)
                        elif item.get("type") == "tool_use":
                            tool_output = self._format_tool_use_for_animation(item, msg)
                            msg_content.append(tool_output)

            # Join content for this message
            if msg_content:
                message_parts.append("".join(msg_content))

        if not message_parts:
            return current_time

        # Add single line spacing before new speaker
        events.append([current_time, "o", "\r\n"])
        current_time += 0.1

        # Add role label
        if role == "user":
            role_label = "👤 Human: "
        elif role == "assistant":
            role_label = "🤖 Assistant: "
        else:
            role_label = f"[{role}]: "

        # Apply emoji fallbacks if enabled
        role_label = self._replace_emoji_with_fallbacks(role_label)
        events.append([current_time, "o", role_label])

        current_time += 0.2  # Pause after role label

        # Type out each message part
        for i, part in enumerate(message_parts):
            if i > 0:
                # Add single line spacing between parts
                events.append([current_time, "o", "\r\n"])
                current_time += 0.2
                # Indent continuation parts to align with content
                events.append([current_time, "o", "  "])
                current_time += 0.1

            # Convert markdown to plain text for animation
            plain_text = self._markdown_to_plain_text(part)

            # Apply emoji fallbacks if enabled
            plain_text = self._replace_emoji_with_fallbacks(plain_text)

            # Handle multi-line content with proper indentation
            lines = plain_text.replace("\r\n", "\n").split("\n")
            for line_idx, line in enumerate(lines):
                # Check time limit before each line
                if self.max_duration and current_time >= self.max_duration:
                    # Add truncation indicator and return
                    truncate_msg = " [...]"
                    for char in truncate_msg:
                        events.append([current_time, "o", char])
                        current_time += self.typing_speed
                    return current_time

                if line_idx > 0:
                    events.append([current_time, "o", "\r\n"])
                    current_time += 0.1
                    # Indent continuation lines to align with content
                    if line.strip():  # Don't indent empty lines
                        events.append([current_time, "o", "  "])
                        current_time += 0.05

                # Type character by character
                for char in line:
                    # Check time limit frequently during long messages
                    if self.max_duration and current_time >= self.max_duration:
                        truncate_msg = " [...]"
                        for trunc_char in truncate_msg:
                            events.append([current_time, "o", trunc_char])
                            current_time += self.typing_speed
                        return current_time

                    events.append([current_time, "o", char])
                    current_time += self.typing_speed

            # Small pause at end of each part
            current_time += 0.3

        events.append([current_time, "o", "\r\n"])
        current_time += 0.1

        return current_time

    def _format_tool_use_for_animation(self, tool_use: dict[str, Any], msg: dict[str, Any]) -> str:
        """Format a tool use for animation display."""
        tool_name = tool_use.get("name", "Unknown Tool")
        tool_id = tool_use.get("id")

        # Find the tool result
        tool_result = None
        if tool_id:
            msg_uuid = msg.get("uuid")
            if msg_uuid and msg_uuid in self._tool_results:
                tool_result = self._tool_results[msg_uuid]
            elif tool_id in self._tool_results:
                tool_result = self._tool_results[tool_id]

        # Create a clean, animation-friendly tool format
        output = f"\r\n🔧 Using {tool_name}"

        # Add tool parameters if available
        if "input" in tool_use and tool_use["input"]:
            params = tool_use["input"]
            if isinstance(params, dict) and params:
                # Show key parameters (limit for readability)
                key_params = []
                for key, value in list(params.items())[:3]:  # Show first 3 params
                    if isinstance(value, str) and len(value) < 50:
                        key_params.append(f"{key}={value}")
                    elif not isinstance(value, dict | list):
                        key_params.append(f"{key}={value}")

                if key_params:
                    output += f" ({', '.join(key_params)})"

        output += "\r\n"

        # Add tool result if available
        if tool_result:
            if isinstance(tool_result, dict) and "text" in tool_result:
                result_text = tool_result["text"]
            else:
                result_text = str(tool_result)

            # Limit result length for animation
            if len(result_text) > 200:
                result_text = result_text[:197] + "..."

            output += f"✓ Result: {result_text}\r\n"

        # Apply emoji fallbacks to the tool output
        output = self._replace_emoji_with_fallbacks(output)
        return output

    def _parse_special_tags(self, content: str) -> str:
        """Parse special tags in content for plain text output."""
        # Remove command-message tags but keep content
        content = re.sub(r"<command-message>(.*?)</command-message>", r"\1", content, flags=re.DOTALL)

        # Remove command-name tags but keep content
        content = re.sub(r"<command-name>(.*?)</command-name>", r"\1", content, flags=re.DOTALL)

        # Remove system-reminder tags but keep content with System prefix
        content = re.sub(
            r"<system-reminder>(.*?)</system-reminder>",
            r"System: \1",
            content,
            flags=re.DOTALL,
        )

        return content

    def _markdown_to_plain_text(self, markdown_text: str) -> str:
        """Convert markdown to plain text for animation."""
        # Remove markdown formatting but keep the text readable

        # Headers
        text = re.sub(r"^#{1,6}\s+", "", markdown_text, flags=re.MULTILINE)

        # Bold/italic
        text = re.sub(r"\*\*\*(.*?)\*\*\*", r"\1", text)  # Bold italic
        text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)  # Bold
        text = re.sub(r"\*(.*?)\*", r"\1", text)  # Italic
        text = re.sub(r"__(.*?)__", r"\1", text)  # Bold
        text = re.sub(r"_(.*?)_", r"\1", text)  # Italic

        # Code blocks - preserve with simple formatting
        text = re.sub(r"```[\w]*\n(.*?)\n```", r"Code:\n\1", text, flags=re.DOTALL)
        text = re.sub(r"`([^`]+)`", r"[\1]", text)  # Inline code

        # Links
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)

        # Lists - convert to simple format
        text = re.sub(r"^\s*[-*+]\s+", "• ", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*\d+\.\s+", "• ", text, flags=re.MULTILINE)

        return text

    def _strip_rich_markup(self, text: str) -> str:
        """Strip Rich console markup from text."""
        # Remove Rich markup like [bold red], [/bold red], etc.
        text = re.sub(r"\[/?[^\]]+\]", "", text)
        return text

    def _replace_emoji_with_fallbacks(self, text: str) -> str:
        """Replace emoji with text fallbacks if enabled."""
        if not self.use_emoji_fallbacks:
            return text

        # Replace each emoji with its text fallback
        for emoji, fallback in EMOJI_FALLBACKS.items():
            text = text.replace(emoji, fallback)

        return text
