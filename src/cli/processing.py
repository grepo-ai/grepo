import queue
from src.agent.main import initiate_agent
from rich.text import Text


def bg_query_processing(
    root_dir,
    buffer,
    console,
    renderable_splits,
    session_uuid,
    model="claude-sonnet-4-20250514",
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
    )

    while not stop_event.is_set():
        try:
            query = query_queue.get(timeout=1)

            if query is not None:
                renderable_splits._agent_logs.add(
                    Text(f"\n{query}\n", style="#CCCCCC on #333333")
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
        buffered_messages = renderable_splits._agent_logs
        while output_queue:
            message, console = output_queue.popleft()
            if message:
                buffered_messages.add(message)

        # print(buffered_messages)
        # if buffered_messages.messages:
        #     renderable_splits.update_upper_split(renderable_data=buffered_messages)
