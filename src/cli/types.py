"""
CLI type definitions: stdio protocol message types and shared aliases.
"""

from __future__ import annotations

import queue
from typing import Any, Literal, TypedDict, Union

# ---------------------------------------------------------------------------
# Stdin (UI -> backend): value types
# ---------------------------------------------------------------------------


class InitValue(TypedDict):
    status: bool
    rootDir: str


# ---------------------------------------------------------------------------
# Stdout (backend -> UI): value types
# ---------------------------------------------------------------------------


class ReadyValue(TypedDict):
    status: bool


class StatusValue(TypedDict, total=False):
    busy: bool
    thinking: bool
    compaction: bool


class ToolStartValue(TypedDict, total=False):
    id: str
    name: str
    args: dict[str, Any]
    data: str | None


class ToolResultValue(TypedDict, total=False):
    id: str
    name: str
    content: str | list[Any]
    format: str  # list_files | read_file | grep | glob | code | raw | error


class CostValue(TypedDict, total=False):
    total_input_tokens: int
    total_output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    cost: str
    context_window_used: str


class InterruptValue(TypedDict, total=False):
    old_code: str
    new_code: str


# ---------------------------------------------------------------------------
# Message type literals
# ---------------------------------------------------------------------------

StdinType = Literal["init", "query", "set_thinking", "cancel"]
StdoutType = Literal[
    "ready",
    "status",
    "delta",
    "done",
    "error",
    "tool_start",
    "tool_result",
    "thinking",
    "cost",
    "interrupt",
]

# ---------------------------------------------------------------------------
# Stdin message shapes (for parsing received lines in backend)
# ---------------------------------------------------------------------------

StdinMessage = Union[
    tuple[Literal["init"], InitValue],
    tuple[Literal["query"], str],
    tuple[Literal["set_thinking"], bool],
    tuple[Literal["cancel"], Any],
]

# ---------------------------------------------------------------------------
# Stdout message value union (for validated emission from backend)
# ---------------------------------------------------------------------------

StdoutValue = (
    ReadyValue
    | StatusValue
    | str
    | None
    | ToolStartValue
    | ToolResultValue
    | CostValue
    | InterruptValue
)

# ---------------------------------------------------------------------------
# Backend stdio: writer queue carries protocol dicts or None sentinel
# ---------------------------------------------------------------------------

WriterQueue = queue.Queue[dict[str, Any] | None]
