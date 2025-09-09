import time
import queue
import threading


def bg_query_processing(
    buffer, console, query_queue=None, output_queue=None, lock=None, stop_event=None
):
    while not stop_event.is_set():
        try:
            query = query_queue.get(timeout=1)
            if query:
                output_queue.append(f"{query}")

        except queue.Empty:
            continue


def bg_query_logs_processing(
    renderable_splits, console, output_queue=None, lock=None, stop_event=None
):
    while not stop_event.is_set():
        renderable_splits.update_upper_split()
        renderable_splits.update_spinner(spin_it=False)
