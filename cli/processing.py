import time


def bg_query_processing(buffer, stop_event, query_queue, console):
    console.log("Running thread logic")

    while not stop_event.is_set():
        while not query_queue.empty():
            query = query_queue.get()
            console.log(f"----- {query} -----")
            time.sleep(3)
        else:
            console.log("waiting for next query...")
            time.sleep(1)
