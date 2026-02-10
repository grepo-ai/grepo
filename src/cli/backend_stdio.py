"""
Stdio driver: read NDJSON from stdin, run agent stream, write NDJSON to stdout.
Writer thread drains a queue; None = sentinel. Errors logged with full traceback to stderr.
"""

from __future__ import annotations

import json
import os
import queue
import re
import sys
import threading
import traceback
from typing import Any, TextIO, cast

from langchain_core.messages import AIMessage, HumanMessage

from agent.main import Agent, initiate_agent
from agent.stream_text import extract_ordered_events
from agent.utils import (
    construct_code,
    format_glob_results,
    format_grep_results,
    format_list_files_results,
    generate_session_uuid,
    preprocess_dir,
)
from cli.stdio_protocol import msg, parse_stdin, parse_stdin_strict
from cli.types import InitValue, StdoutType, WriterQueue
from cli.utils import (
    check_models_api_key,
    create_sqlite_connection,
    get_env_vars,
    get_or_create_settings,
    update_env_var_api_keys,
)

TOOL_SHORT_NAMES = {
    "list_files": "list",
    "read_file": "read",
    "glob": "glob",
    "grep": "grep",
    "get_code_block": "code_search",
    "write": "write",
}


def _log_error(exc: BaseException) -> None:
    """Log exception with full traceback to stderr for debugging."""
    sys.stderr.write(f"[grepo backend] error: {exc}\n")
    traceback.print_exc(file=sys.stderr)
    sys.stderr.flush()


def _log_send(type_: str, value: Any = None, max_len: int = 120) -> None:
    """Log outbound event type; for delta/thinking include value preview."""
    if type_ in ("delta", "thinking") and value is not None:
        preview = (
            value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        )[:max_len]
        preview = preview.replace("\n", "\\n").replace("\r", "\\r")
        if len(value if isinstance(value, str) else json.dumps(value)) > max_len:
            preview += "…"
        sys.stderr.write(f"[grepo] → {type_} {preview!r}\n")
    elif type_ not in ("delta", "thinking"):
        sys.stderr.write(f"[grepo] → {type_}\n")
    sys.stderr.flush()


def _log_recv(type_: str) -> None:
    """Log inbound event type from UI."""
    sys.stderr.write(f"[grepo] ← {type_}\n")
    sys.stderr.flush()


def _writer_thread(out_queue: WriterQueue, stream: TextIO) -> None:
    """Drain queue; write NDJSON lines. None = exit."""
    while True:
        try:
            item = out_queue.get(timeout=0.5)
        except queue.Empty:
            continue

        if item is None:
            break
        try:
            t, v = item.get("type", "?"), item.get("value")
            _log_send(t, v)
            stream.write(json.dumps(item, ensure_ascii=False) + "\n")
            stream.flush()
        except (BrokenPipeError, OSError):
            break


def _tool_result(tool_id: str, name: str, content: Any, format: str) -> dict[str, Any]:
    return {"id": tool_id, "name": name, "content": content, "format": format}


def _tool_start_data(name: str, args: dict[str, Any]) -> str | None:
    if name == "list_files":
        return re.sub(r"\\([^\w\s])", r"\1", args.get("dir_path", ""))
    if name in ("glob", "grep", "get_code_block", "write"):
        return re.sub(
            r"\\([^\w\s])",
            r"\1",
            args.get("pattern") or args.get("file_path") or args.get("pathname") or "",
        )
    return None


def _handle_agent_chunk(
    stream_message: dict[str, Any],
    agent: Agent,
    writer_queue: WriterQueue,
) -> None:
    """Emit deltas/thinking and tool_start from one agent stream chunk.

    Ordering is important for the TUI:
    - First, stream assistant text (delta) and thinking so the UI can render them immediately.
    - Then, emit tool_start so the tool tree node is attached *after* the text.
    - Finally, tool_result events (handled elsewhere) populate the node children.
    """
    ai_message = stream_message["agent"]["messages"][0]
    tool_calls: list[dict[str, Any]] = []

    # Collect tool_calls first so we can emit their tool_start events
    # *after* the assistant deltas/thinking for this chunk.
    if isinstance(ai_message, AIMessage) and getattr(ai_message, "tool_calls", None):
        for tc in ai_message.tool_calls:
            name = tc.get("name") or ""
            args = tc.get("args") or {}
            tid = tc.get("id")
            short = TOOL_SHORT_NAMES.get(name, name)
            data = _tool_start_data(name, args)
            tool_calls.append(
                {"id": tid, "name": short, "args": args, "data": data}
            )

    # Emit thinking/delta events first so streaming text is rendered immediately.
    for kind, chunk in extract_ordered_events(stream_message):
        if kind == "thinking":
            writer_queue.put(msg("thinking", chunk))
        else:
            writer_queue.put(msg("delta", chunk))

    # Now emit tool_start events so the UI can create tree nodes that
    # appear *after* the streamed assistant text.
    for tc in tool_calls:
        writer_queue.put(msg("tool_start", tc))


def _handle_tool_result(
    tool_name: str,
    tool_id: str,
    tool_message: str | None,
    root_dir: str,
    writer_queue: WriterQueue,
) -> None:
    """Emit one tool_result message based on tool name and content."""
    put = lambda c, f: writer_queue.put(
        msg(
            "tool_result",
            _tool_result(tool_id, TOOL_SHORT_NAMES.get(tool_name, tool_name), c, f),
        )
    )

    if tool_name == "list_files":
        if tool_message and "Error: ValueError" in tool_message:
            put("No files found", "error")
        else:
            files_paths, _ = format_list_files_results(tool_message or "")
            paths = files_paths if isinstance(files_paths, list) else [files_paths]
            put(
                [{"path": p, "root": root_dir, "line": 1} for p in paths],
                "list_files",
            )
    elif tool_name == "read_file":
        if tool_message is None:
            return
        if tool_message.startswith("Error:"):
            put(tool_message, "error")
            return
        try:
            data = json.loads(tool_message)
            snippet, path = construct_code(data, truncate=True)
            put([{"path": path, "snippet": snippet, "line": 1}], "read_file")
        except Exception:
            put(tool_message, "raw")
    elif tool_name == "grep":
        if tool_message and tool_message.startswith("Error:"):
            put("Error: Not found", "error")
            return
        results = format_grep_results(tool_message or "")
        items = []
        for file_path, line_suffix in results:
            # line_suffix is typically like ":123" from format_grep_results
            line_str = str(line_suffix).lstrip(":")
            try:
                line_num = int(line_str)
            except ValueError:
                line_num = None
            items.append({"path": file_path, "line": line_num})
        put(items, "grep")
    elif tool_name == "get_code_block":
        if tool_message and not tool_message.startswith("Error:"):
            put(tool_message, "code")
    elif tool_name == "glob":
        if tool_message and tool_message.startswith("Error:"):
            return
        fmt = format_glob_results(tool_message or "") or []
        put([{"path": p, "root": root_dir, "line": 1} for p in fmt], "glob")
    elif tool_name == "write":
        if tool_message and tool_message.startswith("Error:"):
            put(tool_message, "error")


def _run_query_stream(
    agent: Agent,
    text: str,
    writer_queue: WriterQueue,
    cancel_event: threading.Event,
) -> None:
    """Run agent stream; push protocol events to writer_queue. Respect cancel_event."""
    input_type = {"messages": [HumanMessage(content=text)]}
    agent_cycle_active = True

    while agent_cycle_active:
        writer_queue.put(
            msg(
                "status",
                {"busy": True, "thinking": bool(agent.thinking), "compaction": False},
            )
        )
        try:
            for stream_message in agent.stream(input_type):
                if cancel_event.is_set():
                    break
                if stream_message.get("agent"):
                    _handle_agent_chunk(stream_message, agent, writer_queue)
                elif stream_message.get("tools"):
                    msgs = stream_message["tools"]["messages"][0]
                    _handle_tool_result(
                        msgs.name,
                        msgs.tool_call_id,
                        msgs.content,
                        agent.agent_state.values.get("root_dir") or "",
                        writer_queue,
                    )

            all_messages = agent.get_messages()
            if not all_messages:
                agent_cycle_active = False
                continue
            last_ai = next(
                (m for m in reversed(all_messages) if isinstance(m, AIMessage)), None
            )
            if last_ai is None:
                agent_cycle_active = False
                continue
            stop = last_ai.response_metadata.get("stop_reason")
            has_tools = (
                getattr(last_ai, "tool_calls", None) and len(last_ai.tool_calls) > 0
            )
            agent_cycle_active = not (stop == "end_turn" and not has_tools)

        except Exception as e:
            _log_error(e)
            writer_queue.put(msg("error", str(e)))
            agent_cycle_active = False

    try:
        cost = agent.calculate_cycle_cost(render=False)
        if cost:
            writer_queue.put(msg("cost", cost))
    except Exception:
        pass
    writer_queue.put(msg("done", None))
    writer_queue.put(
        msg(
            "status",
            {
                "busy": False,
                "thinking": bool(agent.thinking),
                "compaction": agent._active_auto_compaction,
            },
        )
    )


def _shutdown(
    writer_queue: WriterQueue, writer_thread: threading.Thread, timeout: float = 2
) -> None:
    writer_queue.put(None)
    writer_thread.join(timeout=timeout)


def main() -> None:
    real_stdout: TextIO = sys.stdout
    sys.stdout = sys.stderr

    writer_queue: WriterQueue = queue.Queue()
    writer = threading.Thread(
        target=_writer_thread, args=(writer_queue, real_stdout), daemon=True
    )
    writer.start()

    def send(type_: StdoutType, value: Any) -> None:
        writer_queue.put(msg(type_, value))

    def fail(message: str) -> None:
        send("error", message)
        sys.stderr.write(f"[grepo backend] fatal: {message}\n")
        sys.stderr.flush()
        _shutdown(writer_queue, writer, 2)
        sys.exit(1)

    try:
        line = sys.stdin.readline()
        if not line:
            _shutdown(writer_queue, writer, 2)
            return

        try:
            parsed = parse_stdin_strict(line)
        except ValueError as e:
            _log_error(e)
            fail("First message must be {type:'init', value:{...}}")
        if parsed[0] != "init":
            fail("First message must be {type:'init', value:{...}}")

        _log_recv("init")
        init_value = cast(InitValue, parsed[1])
        status_flag = bool(init_value.get("status"))
        if not status_flag:
            fail("Unsupported protocol status")

        root_dir = init_value.get("rootDir") or os.getcwd()
        os.makedirs(f"{root_dir}/.grepo", exist_ok=True)
        sqlite_con = create_sqlite_connection(root_dir)
        settings_json = get_or_create_settings(root_dir)
        env_vars = get_env_vars()
        available_model_keys = check_models_api_key(env_vars, settings_json, root_dir)
        if not available_model_keys:
            fail(
                "Missing model API key. Set ANTHROPIC_API_KEY or add to .grepo/settings.json"
            )
        update_env_var_api_keys(available_model_keys, settings_json, root_dir)
        preprocessed_data = preprocess_dir(root_dir)
        session_uuid = generate_session_uuid()
        agent = initiate_agent(
            root_dir=root_dir,
            session_uuid=session_uuid,
            output_queue=queue.Queue(),
            model_provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            preprocessed_data=preprocessed_data,
            sqlite_con=sqlite_con,
        )
        send("ready", {"status": True})

        cancel_event = threading.Event()
        while True:
            line = sys.stdin.readline()
            if not line:
                break
            parsed = parse_stdin(line)
            if parsed is None:
                send("error", "Invalid JSON or unknown message shape")
                continue
            m_type, m_value = parsed
            _log_recv(m_type)

            if m_type == "set_thinking":
                try:
                    thinking_on = bool(m_value)
                    agent.thinking = thinking_on
                    send("status", {"thinking": thinking_on})
                except Exception as e:
                    _log_error(e)
                    send("error", str(e))
                continue
            if m_type == "cancel":
                cancel_event.set()
                continue
            if m_type == "query":
                if not isinstance(m_value, str) or not m_value.strip():
                    send("error", "Query value must be a non-empty string")
                    continue
                cancel_event.clear()
                _run_query_stream(agent, m_value.strip(), writer_queue, cancel_event)
                continue
            send("error", f"Unknown type: {m_type}")

    except Exception as e:
        _log_error(e)
        send("error", str(e))
    finally:
        _shutdown(writer_queue, writer, 3)
        try:
            sys.stdout.flush()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.stderr.write("[grepo backend] uncaught exception:\n")
        sys.stderr.flush()
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        sys.exit(1)
