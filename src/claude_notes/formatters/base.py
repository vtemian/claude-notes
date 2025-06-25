"""Base formatter classes for Claude conversations."""

from abc import ABC, abstractmethod
from typing import Any


class BaseFormatter(ABC):
    """Abstract base class for conversation formatters."""

    def __init__(self):
        """Initialize the formatter."""
        self._tool_results = {}

    @abstractmethod
    def format_conversation(self, messages: list[dict[str, Any]], conversation_info: dict[str, Any]) -> str:
        """Format and return a conversation as a string.

        Args:
            messages: List of message dictionaries
            conversation_info: Conversation metadata

        Returns:
            Formatted conversation string
        """
        pass

    @abstractmethod
    def format_tool_use(self, tool_name: str, tool_use: dict[str, Any], tool_result: str | None = None) -> str:
        """Format a tool use with its result.

        Args:
            tool_name: Name of the tool
            tool_use: Tool usage data
            tool_result: Tool execution result

        Returns:
            Formatted tool use string
        """
        pass

    def _collect_tool_results(self, messages: list[dict[str, Any]]) -> None:
        """Collect tool results and map them to their parent tool uses."""
        # Map tool results by looking for user messages after tool uses
        for i, msg in enumerate(messages):
            if msg.get("type") == "assistant" and msg.get("uuid"):
                # Check if this assistant message has tool uses
                message_data = msg.get("message", {})
                content = message_data.get("content", [])
                has_tool_use = False

                if isinstance(content, list):
                    for item in content:
                        if isinstance(item, dict) and item.get("type") == "tool_use":
                            has_tool_use = True
                            break

                if has_tool_use:
                    # Look for the next user message which should contain the result
                    for j in range(i + 1, min(i + 5, len(messages))):
                        next_msg = messages[j]
                        if next_msg.get("type") == "user":
                            next_content = next_msg.get("message", {}).get("content", "")
                            tool_result_content = None

                            # Handle both string and list formats
                            if isinstance(next_content, str) and next_content.strip():
                                # Old format: string starting with "Tool Result:"
                                if next_content.strip().startswith("Tool Result:"):
                                    tool_result_content = next_content.strip()[12:].strip()  # Remove "Tool Result:"
                            elif isinstance(next_content, list):
                                # New format: list with tool_result dict
                                for item in next_content:
                                    if isinstance(item, dict) and item.get("type") == "tool_result":
                                        tool_result_content = item.get("content", "")
                                        break

                            if tool_result_content:
                                # Remove system reminder messages that get appended
                                if "<system-reminder>" in tool_result_content:
                                    tool_result_content = tool_result_content.split("<system-reminder>")[0].strip()

                                # Check if there's additional structured data in toolUseResult
                                if "toolUseResult" in next_msg:
                                    tool_data = next_msg["toolUseResult"]
                                    # For Edit/MultiEdit tools, we want the structured patch data
                                    if isinstance(tool_data, dict) and any(
                                        key in tool_data for key in ["structuredPatch", "edits", "filePath"]
                                    ):
                                        # Store both the text result and structured data
                                        self._tool_results[msg["uuid"]] = {
                                            "text": tool_result_content,
                                            "structured_data": tool_data,
                                        }
                                    else:
                                        self._tool_results[msg["uuid"]] = tool_result_content
                                else:
                                    self._tool_results[msg["uuid"]] = tool_result_content
                                break
                        elif next_msg.get("type") == "tool_result":
                            # Direct tool result
                            result = next_msg.get("message", "")
                            if isinstance(result, dict):
                                result = result.get("content", str(result))
                            self._tool_results[msg["uuid"]] = str(result)

                            # Also check toolUseResult field
                            if "toolUseResult" in next_msg:
                                tool_result = next_msg["toolUseResult"]
                                if isinstance(tool_result, str):
                                    self._tool_results[msg["uuid"]] = tool_result
                                elif isinstance(tool_result, dict):
                                    self._tool_results[msg["uuid"]] = tool_result.get("content", str(tool_result))
                            break

    def _group_messages(self, messages: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
        """Group consecutive messages by the same role."""
        if not messages:
            return []

        groups = []
        current_group = []
        current_role = None

        for msg in messages:
            # Skip tool results - they're handled inline with tool uses
            if msg.get("type") == "tool_result":
                continue

            # Also skip user messages that are just tool results - they appear inline now
            if msg.get("type") == "user":
                message_data = msg.get("message", {})
                if isinstance(message_data, dict):
                    content = message_data.get("content", "")
                    if isinstance(content, str) and content.strip().startswith("Tool Result:"):
                        continue

            # Extract the actual message from the structure
            if "message" in msg and isinstance(msg["message"], dict):
                message_data = msg["message"]
                role = message_data.get("role")

                # Skip meta messages or messages without role
                if msg.get("isMeta") or not role:
                    continue

                if role != current_role:
                    if current_group:
                        groups.append(current_group)
                    current_group = [msg]
                    current_role = role
                else:
                    current_group.append(msg)

        if current_group:
            groups.append(current_group)

        return groups


class OutputFormat:
    """Enumeration of supported output formats."""

    TERMINAL = "terminal"
    HTML = "html"
