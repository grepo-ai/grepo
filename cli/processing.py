import time


def bg_query_processing(
    buffer, console, query_queue=None, output_queue=None, lock=None, stop_event=None
):
    while not stop_event.is_set():
        # console.log(len(output_queue))
        # console.log(query_queue.qsize())
        # console.log("--- background thread ---")

        while not query_queue.empty():
            query = query_queue.get()

            if query:
                with lock:
                    output_queue.append(f"{query}")

        else:
            time.sleep(1)


def bg_query_logs_processing(
    renderable_splits, console, output_queue=None, lock=None, stop_event=None
):
    while not stop_event.is_set():
        renderable_splits.update_upper_split()
        renderable_splits.update_spinner(spin_it=False)
