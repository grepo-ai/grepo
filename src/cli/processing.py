import queue
from src.agent.main import invoke_agent, initiate_agent


def bg_query_processing(
    buffer,
    console,
    renderable_splits,
    query_queue=None,
    output_queue=None,
    lock=None,
    stop_event=None,
):
    # --- Initiate Agent --- #
    session_uuid, agent_dict, llm_client, ui_renders = initiate_agent()

    while not stop_event.is_set():
        try:
            query = query_queue.get(timeout=1)

            if query is not None:
                console.print(f"[#F47AFF]\n{query}[/]")
                renderable_splits.update_upper_split(renderable_data=" ")

                invoke_agent(
                    renderable_splits,
                    session_uuid,
                    agent_dict,
                    llm_client,
                    ui_renders,
                    query.strip(">"),
                    output_queue,
                )

        except queue.Empty:
            continue


def bg_query_logs_processing(
    renderable_splits, console, output_queue=None, lock=None, stop_event=None
):
    while not stop_event.is_set():
        buffered_messages = []
        while output_queue:
            message, console = output_queue.popleft()
            if message:
                buffered_messages.append(message)

        # TODO: Complete the logic as list of logs cannot be rendered right away this TODO is attached to
        # AgentLogs TODO
        if buffered_messages:
            renderable_splits.update_upper_split(renderable_data=buffered_messages)
