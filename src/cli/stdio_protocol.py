"""
NDJSON stdio protocol shared with the UI
Single structured message schema: TypedDicts and strict validation on parse/emit.
"""

from __future__ import annotations

import json
from typing import Any, cast

from cli.types import (
    CostValue,
    InitValue,
    InterruptValue,
    ReadyValue,
    StatusValue,
    StdinMessage,
    StdoutType,
    StdoutValue,
    ToolResultValue,
    ToolStartValue,
)

# Re-export types so "from cli.stdio_protocol import StdinMessage" etc. still work
__all__ = [
    "CostValue",
    "InitValue",
    "InterruptValue",
    "ReadyValue",
    "StatusValue",
    "StdinMessage",
    "StdoutType",
    "StdoutValue",
    "ToolResultValue",
    "ToolStartValue",
    "msg",
    "parse_stdin",
    "parse_stdin_strict",
]


def _validate_ready(value: ReadyValue) -> None:
    if not isinstance(value.get("status"), bool):
        raise TypeError("ready.value.status must be bool")


def _validate_status(value: StatusValue) -> None:
    v = value
    if "busy" in v and not isinstance(v["busy"], bool):
        raise TypeError("status.value.busy must be bool")
    if "thinking" in v and not isinstance(v["thinking"], bool):
        raise TypeError("status.value.thinking must be bool")
    if "compaction" in v and not isinstance(v["compaction"], bool):
        raise TypeError("status.value.compaction must be bool")


def _validate_tool_start(value: ToolStartValue) -> None:
    if not isinstance(value.get("id"), str):
        raise TypeError("tool_start.value.id must be str")
    if not isinstance(value.get("name"), str):
        raise TypeError("tool_start.value.name must be str")
    if not isinstance(value.get("args"), dict):
        raise TypeError("tool_start.value.args must be dict")


def _validate_tool_result(value: ToolResultValue) -> None:
    if not isinstance(value.get("id"), str):
        raise TypeError("tool_result.value.id must be str")
    if not isinstance(value.get("name"), str):
        raise TypeError("tool_result.value.name must be str")
    c = value.get("content")
    if not (isinstance(c, str) or (isinstance(c, list))):
        raise TypeError("tool_result.value.content must be str or list")


def _validate_cost(value: CostValue) -> None:
    if not isinstance(value.get("total_input_tokens"), (int, float)):
        raise TypeError("cost.value.total_input_tokens must be number")
    if not isinstance(value.get("total_output_tokens"), (int, float)):
        raise TypeError("cost.value.total_output_tokens must be number")
    if "cost" in value and not isinstance(value["cost"], str):
        raise TypeError("cost.value.cost must be str")
    if "context_window_used" in value and not isinstance(
        value["context_window_used"], str
    ):
        raise TypeError("cost.value.context_window_used must be str")


def msg(type_: StdoutType, value: StdoutValue) -> dict[str, Any]:
    """Build a validated stdout message. Raises TypeError if value shape is invalid."""
    if type_ == "ready":
        _validate_ready(cast(ReadyValue, value))
    elif type_ == "status":
        _validate_status(cast(StatusValue, value))
    elif type_ == "delta":
        if not isinstance(value, str):
            raise TypeError("delta.value must be str")
    elif type_ == "done":
        if value is not None:
            raise TypeError("done.value must be None")
    elif type_ == "error":
        if not isinstance(value, str):
            raise TypeError("error.value must be str")
    elif type_ == "tool_start":
        _validate_tool_start(cast(ToolStartValue, value))
    elif type_ == "tool_result":
        _validate_tool_result(cast(ToolResultValue, value))
    elif type_ == "thinking":
        if not isinstance(value, str):
            raise TypeError("thinking.value must be str")
    elif type_ == "cost":
        _validate_cost(cast(CostValue, value))
    elif type_ == "interrupt":
        if not isinstance(value, dict):
            raise TypeError("interrupt.value must be dict")
    return {"type": type_, "value": value}


# ---------------------------------------------------------------------------
# Parse stdin (strict: only accept valid StdinMessage shapes)
# ---------------------------------------------------------------------------


def parse_stdin(line: str) -> StdinMessage | None:
    """
    Parse one NDJSON line from UI. Returns (type, value) if valid StdinMessage, else None.
    For invalid JSON or unknown/ill-formed message, returns None.
    """
    raw = line.strip()
    if not raw:
        return None
    try:
        obj = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(obj, dict) or "type" not in obj or "value" not in obj:
        return None
    t = obj["type"]
    v = obj["value"]
    if t == "init":
        if isinstance(v, dict) and isinstance(v.get("status"), bool) and "rootDir" in v:
            return (
                "init",
                cast(
                    InitValue,
                    {
                        "status": bool(v["status"]),
                        "rootDir": str(v.get("rootDir", "")),
                    },
                ),
            )
        return None
    if t == "query":
        if isinstance(v, str):
            return ("query", v)
        return None
    if t == "set_thinking":
        if isinstance(v, bool):
            return ("set_thinking", v)
        return None
    if t == "cancel":
        return ("cancel", v)
    return None


def parse_stdin_strict(line: str) -> StdinMessage:
    """
    Parse one NDJSON line from UI. Raises ValueError if not a valid StdinMessage.
    Use when backend requires a valid message (e.g. first init line).
    """
    parsed = parse_stdin(line)
    if parsed is None:
        raise ValueError("Invalid or unknown stdin message")
    return parsed
