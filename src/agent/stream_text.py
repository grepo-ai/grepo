from __future__ import annotations


def _text_from_part(part: object) -> str | None:
    """Get text from a content block (dict with 'text' or object with .text / type 'text')."""
    if part is None:
        return None
    if isinstance(part, dict):
        t = part.get("text")
        if isinstance(t, str) and t:
            return t
        if part.get("type") == "text":
            t = part.get("text")
            if isinstance(t, str) and t:
                return t
        return None
    if isinstance(part, str) and part:
        return part
    # LangChain content block objects (e.g. TextContentBlock)
    t = getattr(part, "text", None)
    if isinstance(t, str) and t:
        return t
    t = getattr(part, "content", None)
    if isinstance(t, str) and t:
        return t
    return None


def extract_text_deltas(stream_message: dict) -> list[str]:
    """
    Extract assistant text chunks from langgraph stream updates.
    Intended for non-Rich UIs (Ink/WebSocket/etc).
    Handles content as: list of dicts (with "text" or type "text"), plain string, or objects with .text/.content.
    """
    if not stream_message.get("agent"):
        return []

    messages = stream_message["agent"].get("messages")
    if not messages:
        return []
    ai_message = messages[0]
    content = (
        getattr(ai_message, "content", None)
        if not isinstance(ai_message, dict)
        else ai_message.get("content")
    )

    deltas: list[str] = []
    if content is None:
        return []
    if isinstance(content, list):
        for part in content:
            text = _text_from_part(part)
            if text:
                deltas.append(text)
    elif isinstance(content, str) and content:
        deltas.append(content)

    return deltas


def _thinking_from_part(part: object) -> str | None:
    """Get thinking text from a content block (dict with 'thinking' or type 'thinking')."""
    if part is None:
        return None
    if isinstance(part, dict):
        th = part.get("thinking")
        if isinstance(th, str) and th:
            return th
        if part.get("type") == "thinking":
            th = part.get("thinking") or part.get("text") or part.get("content")
            if isinstance(th, str) and th:
                return th
        return None
    th = getattr(part, "thinking", None)
    if isinstance(th, str) and th:
        return th
    return None


def extract_thinking_deltas(stream_message: dict) -> list[str]:
    """
    Extract thinking chunks from langgraph stream updates (e.g. Anthropic extended thinking).
    Handles content as: list of dicts with "thinking" or type "thinking", or objects with .thinking.
    """
    if not stream_message.get("agent"):
        return []
    messages = stream_message["agent"].get("messages")
    if not messages:
        return []
    ai_message = messages[0]
    content = (
        getattr(ai_message, "content", None)
        if not isinstance(ai_message, dict)
        else ai_message.get("content")
    )
    if content is None or not isinstance(content, list):
        return []
    result: list[str] = []
    for part in content:
        th = _thinking_from_part(part)
        if th:
            result.append(th)
    return result


def extract_ordered_events(stream_message: dict) -> list[tuple[str, str]]:
    """
    Extract thinking and text chunks from a stream_message in the original content order.
    Returns a list of (kind, text) tuples where kind is \"thinking\" or \"delta\".
    This is used by stdio backends to mimic the TUI agent.invoke rendering order.
    """
    if not stream_message.get("agent"):
        return []
    messages = stream_message["agent"].get("messages")
    if not messages:
        return []
    ai_message = messages[0]
    content = (
        getattr(ai_message, "content", None)
        if not isinstance(ai_message, dict)
        else ai_message.get("content")
    )

    events: list[tuple[str, str]] = []
    if content is None:
        return events

    if isinstance(content, list):
        for part in content:
            th = _thinking_from_part(part)
            if th:
                events.append(("thinking", th))
                continue
            text = _text_from_part(part)
            if text:
                events.append(("delta", text))
    elif isinstance(content, str) and content:
        events.append(("delta", content))

    return events
