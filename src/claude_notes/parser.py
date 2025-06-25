"""Parser for Claude Code transcript JSONL files."""

import json
from pathlib import Path
from typing import Any


class TranscriptParser:
    """Parse Claude Code transcript JSONL files."""

    def __init__(self, file_path: Path):
        """Initialize parser with a transcript file path."""
        self.file_path = file_path
        self.messages: list[dict[str, Any]] = []
        self._parse()

    def _parse(self):
        """Parse the JSONL file."""
        with open(self.file_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        data = json.loads(line)
                        self.messages.append(data)
                    except json.JSONDecodeError as e:
                        print(f"Warning: Failed to parse line in {self.file_path}: {e}")

    def get_conversation_info(self) -> dict[str, Any]:
        """Get basic information about the conversation."""
        if not self.messages:
            return {}

        # Find first and last timestamps
        timestamps = []
        for msg in self.messages:
            if "timestamp" in msg:
                timestamps.append(msg["timestamp"])

        # Count actual messages (not meta messages)
        actual_messages = [m for m in self.messages if not m.get("isMeta", False)]

        info = {
            "file_name": self.file_path.name,
            "message_count": len(actual_messages),
            "total_entries": len(self.messages),
            "start_time": min(timestamps) if timestamps else None,
            "end_time": max(timestamps) if timestamps else None,
        }

        # Try to get conversation ID and session ID
        if self.file_path.stem:
            info["conversation_id"] = self.file_path.stem

        # Try to get session ID from first message
        if self.messages and "sessionId" in self.messages[0]:
            info["session_id"] = self.messages[0]["sessionId"]

        return info

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all messages from the transcript."""
        return self.messages

    def get_summary(self) -> str | None:
        """Try to extract a summary or title from the conversation."""
        # Look for system messages or first user message
        for msg in self.messages:
            if msg.get("type") == "conversation_title":
                return msg.get("content", "")
            elif msg.get("role") == "user" and msg.get("content"):
                # Return first line of first user message as summary
                content = msg["content"]
                if isinstance(content, str):
                    return content.split("\n")[0][:100] + ("..." if len(content) > 100 else "")
        return None
