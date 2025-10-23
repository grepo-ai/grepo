import time
import queue
import threading
from rich.text import Text
from rich.padding import Padding
from agent.main import initiate_agent


def bg_query_processing(
    root_dir,
    buffer,
    console,
    renderable_splits,
    session_uuid,
    preprocessed_data,
    model="claude-sonnet-4-5-20250929",
    model_provider="anthropic",
    query_queue=None,
    output_queue=None,
    lock=None,
    stop_event=None,
):
    # --- Initiate Agent --- #
    agent = initiate_agent(
        root_dir=root_dir,
        session_uuid=session_uuid,
        output_queue=output_queue,
        model=model,
        model_provider=model_provider,
        preprocessed_data=preprocessed_data,
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
                    output_queue.append(
                        (Text(f"\n{query} \n", style="#FAFAFA on #383838"), console)
                    )
                    agent.invoke(
                        renderable_splits,
                        query.strip(">"),
                    )

        except queue.Empty:
            continue


def bg_query_logs_processing(
    renderable_splits, console, output_queue=None, lock=None, stop_event=None
):
    while not stop_event.is_set():
        try:
            # Process all available messages from the deque
            while len(output_queue) > 0:
                message, msg_console = output_queue.popleft()
                if message:
                    # Print logs directly to console above the Live region
                    # (This approach works instead of rendering logs inside a separate container/layout which
                    # introduces extreme complexities of auto-scrolling, making sure the right logs are rendered
                    # in active terminal view, also its IMPORTANT to know `console` being used here
                    # is same that is passed to Live since the threads don't have access to live_region, we need to pass it or use the console
                    # that's already passed (which is the same in this case), so we dont need to do live.console.print()[source: Rich docs])
                    console.print(
                        Padding(message, (0, 0, 0, 1))
                    )  # (top, right, bottom, left)

        except IndexError:
            pass

        time.sleep(0.1)


def compaction_status_updates(renderable_splits, console, agent, stop_event=None):
    while not stop_event.is_set():
        if renderable_splits._commands_palette_active:
            continue

        renderable_splits.update_footer_split(compaction=agent._active_auto_compaction)
        time.sleep(1)
