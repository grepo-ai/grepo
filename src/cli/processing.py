import queue
import threading
import time
from queue import SimpleQueue

from rich.padding import Padding
from rich.text import Text

from agent.main import initiate_agent


def bg_query_processing(
    root_dir,
    buffer,
    console,
    renderable_splits,
    session_uuid,
    preprocessed_data,
    stop_event: threading.Event,
    query_queue: SimpleQueue,
    output_queue: queue.Queue,
    lock: threading.Lock,
    model="claude-sonnet-4-5-20250929",
    model_provider="anthropic",
    sqlite_con=None,
):
    # --- Initiate Agent --- #
    agent = initiate_agent(
        root_dir=root_dir,
        session_uuid=session_uuid,
        output_queue=output_queue,  # ty:ignore[invalid-argument-type]
        model=model,
        model_provider=model_provider,
        preprocessed_data=preprocessed_data,
        sqlite_con=sqlite_con,
    )

    status_thread = threading.Thread(
        target=compaction_status_updates,
        args=(
            renderable_splits,
            console,
            agent,
            stop_event,
        ),
        daemon=True,
    )
    status_thread.start()

    while not stop_event.is_set():
        try:
            query = query_queue.get(timeout=1)

            if query is not None:
                # Thinking mode toggle command
                if query == "\t":
                    agent.thinking = not agent.thinking
                    thinking_flag = True if agent.thinking else False
                    renderable_splits.update_footer_split(thinking=thinking_flag)
                    continue

                else:
                    output_queue.put(
                        (Text(f"\n{query} \n", style="#FAFAFA on #383838"), console)
                    )
                    agent.invoke(
                        renderable_splits,
                        query.strip(">"),
                    )

        except queue.Empty:
            continue


def bg_query_logs_processing(
    renderable_splits,
    console,
    stop_event: threading.Event,
    output_queue: queue.Queue,
    lock: threading.Lock,
):
    while not stop_event.is_set():
        try:
            message, msg_console = output_queue.get(timeout=0.1)
            if message:
                console.print(
                    Padding(message, (0, 0, 0, 1))
                )  # (top, right, bottom, left)
        except queue.Empty:
            continue


def compaction_status_updates(
    renderable_splits, console, agent, stop_event: threading.Event
):
    while not stop_event.is_set():
        if renderable_splits._commands_palette_active:
            continue

        renderable_splits.update_footer_split(compaction=agent._active_auto_compaction)
        time.sleep(1)
