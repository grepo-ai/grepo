import os
import threading
from queue import SimpleQueue
from rich.console import Console
from rich.live import Live
from collections import deque


from src.agent.utils import generate_session_uuid
from src.cli.commands import Commands
from src.cli.terminal import GetchRaw, read_keystroke
from src.cli.processing import bg_query_processing, bg_query_logs_processing
from src.cli.renderables import render_intro, RenderSplits


# Intial screen setup and constants
console = Console(highlight=False)


if __name__ == "__main__":
    # Welcome screen and (add intial model/api-key settings via arrow keys and toggle -> TODO)
    render_intro(console)

    # Get root dir to read AGENTS.md file
    root_dir = os.getcwd()

    # Chat session uuid
    session_uuid = generate_session_uuid()

    # Thread initials
    lock = threading.Lock()
    query_queue = SimpleQueue()
    stop_event = threading.Event()
    output_queue = deque()
    buffer = ""

    # Create split regions for query processing and input bar
    split_screens = RenderSplits(output_queue=output_queue, lock=lock)

    thread_kwargs = {
        "query_queue": query_queue,
        "output_queue": output_queue,
        "lock": lock,
        "stop_event": stop_event,
    }

    # Thread for processing input queries
    input_processing_thread = threading.Thread(
        target=bg_query_processing,
        args=(root_dir, buffer, console, split_screens, session_uuid),
        kwargs=thread_kwargs,
        daemon=True,
    )

    input_processing_thread.start()

    # Thread to process queries in-process logs
    logs_processing_thread = threading.Thread(
        target=bg_query_logs_processing,
        args=(
            split_screens,
            console,
        ),
        kwargs={"output_queue": output_queue, "stop_event": stop_event},
        daemon=True,
    )
    logs_processing_thread.start()

    live_region = Live(
        split_screens,
        refresh_per_second=60,
        console=console,
        transient=False,
    )

    try:
        live_region.start()

        while True:
            with GetchRaw():
                try:
                    while True:
                        char = read_keystroke()

                        if not char:
                            continue

                        # Ignore arrow keys and TODO add other non-printable sequences
                        # that might not need processing
                        if len(char) > 1 or char.startswith("\x1b"):
                            continue

                        # --- Process user's query on `Enter` keystroke ---
                        if char == "\n" and len(buffer) > 0 and buffer[-1] != "\n":
                            query_queue.put(f"> {buffer}")
                            break

                        elif char == "\x7f":  # `Backspace` keystroke
                            buffer = buffer[:-1]

                        # --- TODO: Improve how buffer addition is handled and edge cases better (works for now but improve ---
                        # Handle repeated `Enter` keystrokes
                        else:
                            if not buffer and char == "\n":
                                continue
                            else:
                                buffer += char

                        # Just update the respective rendearble sections Rich picks up the diff and updates renderables
                        # Also we are already auto-refreshing the live region so we dont need to explicitly to call live.update()
                        split_screens.update_lower_split(console, buffer)

                        # Show commands palette and switch live region flow
                        if char == "/" and len(buffer) == 1:
                            split_screens.update_footer_split(list_all_commands=True)
                            output = Commands(
                                console=console, rendered_regions=split_screens
                            ).show()

                            buffer += output
                            split_screens.update_lower_split(console, buffer)
                            split_screens.update_footer_split(blank=True)

                # Ctrl-C keystroke
                except KeyboardInterrupt:
                    split_screens.update_footer_split(exit_screen=True)
                    split_screens.update_lower_split(console, "")
                    stop_event.set()
                    break

            # Reset and clear buffer on `Enter` keystroke i.e submission of query
            buffer = ""
            split_screens.update_lower_split(console, buffer, is_first_time=False)

    finally:
        live_region.stop()
