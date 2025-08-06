import threading
from queue import SimpleQueue
from rich.console import Console
from rich.live import Live
from rich.padding import Padding
from rich.box import Box


from . import (
    render_intro,
    GetchRaw,
    read_keystroke,
    bg_query_processing,
    RenderSplits,
)


# Intial screen setup and constants
console = Console()
blank_box = Box("    \n" * 8, ascii=True)
all_commands = ["help", "config", "ask"]


if __name__ == "__main__":
    # Welcome screen and (add intial model/api-key settings via arrow keys and toggle -> TODO)
    render_intro(console)

    # Thread initials
    lock = threading.Lock()
    query_queue = SimpleQueue()
    stop_event = threading.Event()
    output_queue = []
    buffer = ""

    thread_kwargs = {
        "query_queue": query_queue,
        "output_queue": output_queue,
        "lock": lock,
        "stop_event": stop_event,
    }

    # Start background daemon thread for processing queries
    bg_processing_thread = threading.Thread(
        target=bg_query_processing,
        args=(
            buffer,
            console,
        ),
        kwargs=thread_kwargs,
        daemon=True,
    )
    bg_processing_thread.start()

    # Create split regions for query processing and input bar
    split_screens = RenderSplits(output_queue, blank_box)

    live_region = Live(
        split_screens,
        refresh_per_second=20,
        console=console,
        transient=False,
    )

    try:
        live_region.start()

        while True:
            with GetchRaw() as getch:
                try:
                    while True:
                        # Constantly update the status of input query
                        split_screens.update_upper_split()

                        char = read_keystroke(getch.fd)

                        if not char:
                            continue

                        # Ignore arrow keys and TODO add other non-printable sequences that might not be required
                        if len(char) > 1 or char.startswith("\x1b"):
                            continue

                        # --- Process user's query on `Enter` keystroke ---
                        if char == "\n" and len(buffer) > 0 and buffer[-1] != "\n":
                            query_queue.put(f"> {buffer}")
                            split_screens.update_spinner()
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
                        split_screens.update_upper_split()
                        split_screens.update_lower_split(console, buffer)

                # Ctrl-C keystroke
                except KeyboardInterrupt:
                    stop_event.set()
                    break

            # Reset and clear buffer on `Enter` keystroke i.e submission of query
            buffer = ""
            split_screens.update_lower_split(console, buffer, is_first_time=False)

    finally:
        live_region.stop()
        console.print(Padding("See you soon!", (0, 0, 1, 2)))


# TODO use this later for show `commands`
# Show list of available commands
# if char == "/" and len(buffer) == 1:
#     if not query_queue.empty():
#         command_bar.update(
#             render_command_bar(
#                 render_alert="Cannot use / (list commands) until your queries have been processed",
#             )
#         )
#         continue

#     else:
#         command_bar.update(
#             render_command_bar(
#                 "",
#                 True,
#             )
#         )
#         command_bar.stop()
#         selected_command = show_commands()

#         if selected_command:
#             buffer += selected_command

#         command_bar.start()


# TODO: Refactor and move this to queue based processing
# def invoke_agent(command_bar: Live, buffer: str):
#     # Past user queries
#     console.print(Padding(f"[#D4D4D4]> {buffer}[/]", (1, 0, 0, 1)))

#     spinner = Spinner("star", text="[#FFC375]Thinking real hard...[/]", style="#FFC375")

#     new_live = Live(
#         Panel(spinner, box=blank_box, padding=(0, 0, 0, 0)),
#         refresh_per_second=100,
#         console=console,
#         transient=False,
#     )
#     new_live.start()
#     time.sleep(3)
#     console.print(Padding("Done processing", (1, 0, 0, 1)))
#     new_live.update("")
#     new_live.stop()


# TODO refactor
# def show_commands():
#     live_commands = Live(
#         render_commands_list(blank_box),
#         refresh_per_second=100,
#         console=console,
#         transient=False,
#     )

#     live_commands.start()

#     try:
#         dynamic_selection = -1
#         with GetchRaw() as getch:
#             while True:
#                 char = read_keystroke(getch.fd)

#                 if not char or char not in ("\x1b[A", "\x1b[B", "\x1b", "\n"):
#                     continue

#                 if char == "\x1b":  # ESC key
#                     selected_command = None
#                     break

#                 elif char == "\x1b[B":  # DOWN arrow
#                     dynamic_selection += 1

#                 elif char == "\x1b[A":  # UP arrow
#                     dynamic_selection -= 1

#                 live_commands.update(render_commands_list(blank_box, dynamic_selection))

#                 # Select this command and bring/export it into main input bar
#                 if char == "\n":
#                     if dynamic_selection < 0:
#                         dynamic_selection += 1
#                         selected_command = all_commands[dynamic_selection]
#                         break

#                 # Reset values to avoid overflow
#                 if dynamic_selection == 2 or dynamic_selection == -4:
#                     dynamic_selection = -1

#         return selected_command

#     finally:
#         live_commands.stop()
