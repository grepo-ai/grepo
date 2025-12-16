import threading
import traceback
from cli.processing import bg_query_processing, bg_query_logs_processing


def initiate_threads(
    root_dir,
    buffer,
    console,
    split_screens,
    session_uuid,
    preprocessed_data,
    query_queue,
    output_queue,
    lock,
    stop_event,
    sqlite_con,
):
    thread_kwargs = {
        "query_queue": query_queue,
        "output_queue": output_queue,
        "lock": lock,
        "stop_event": stop_event,
        "sqlite_con": sqlite_con,
    }

    try:
        # Thread for processing input queries
        input_processing_thread = threading.Thread(
            target=bg_query_processing,
            args=(
                root_dir,
                buffer,
                console,
                split_screens,
                session_uuid,
                preprocessed_data,
            ),
            kwargs=thread_kwargs,
            daemon=True,
        )

        # Thread for processing query logs
        logs_processing_thread = threading.Thread(
            target=bg_query_logs_processing,
            args=(
                split_screens,
                console,
            ),
            kwargs={"output_queue": output_queue, "stop_event": stop_event},
            daemon=True,
        )

        return input_processing_thread, logs_processing_thread

    except Exception:
        traceback.print_exc()
        console.log("[Threads] --- Thread initiation failed ---")
