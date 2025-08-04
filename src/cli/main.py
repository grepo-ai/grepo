import os
import sys
import termios
import select
import tty
import time
from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.padding import Padding
from rich.box import HEAVY_EDGE, ROUNDED, DOUBLE_EDGE, HEAVY, Box
import pyfiglet

from src.cli import (
    render_intro,
    render_command_bar,
    render_commands_list,
    GetchRaw,
    read_keystroke,
)
import threading
from queue import SimpleQueue


# Intial screen setup and constants
console = Console()
blank_box = Box("    \n" * 8, ascii=True)
all_commands = ["help", "settings", "search"]


def show_commands():
    live_commands = Live(
        render_commands_list(blank_box),
        refresh_per_second=100,
        console=console,
        transient=False,
    )

    live_commands.start()

    try:
        dynamic_selection = -1
        with GetchRaw() as getch:
            while True:
                char = read_keystroke(getch.fd)

                if not char or char not in ("\x1b[A", "\x1b[B", "\x1b", "\n"):
                    continue

                if char == "\x1b":  # ESC key
                    selected_command = None
                    break

                elif char == "\x1b[B":  # DOWN arrow
                    dynamic_selection += 1

                elif char == "\x1b[A":  # UP arrow
                    dynamic_selection -= 1

                live_commands.update(render_commands_list(blank_box, dynamic_selection))

                # Select this command and bring/export it into main input bar
                if char == "\n":
                    if dynamic_selection < 0:
                        dynamic_selection += 1
                        selected_command = all_commands[dynamic_selection]
                        break

                # Reset values to avoid overflow
                if dynamic_selection == 2 or dynamic_selection == -4:
                    dynamic_selection = -1

        return selected_command

    finally:
        live_commands.stop()


def invoke_agent(command_bar: Live, buffer: str):
    # Past user queries
    console.print(Padding(f"[#D4D4D4]> {buffer}[/]", (1, 0, 0, 1)))

    spinner = Spinner("star", text="[#FFC375]Thinking real hard...[/]", style="#FFC375")

    new_live = Live(
        Panel(spinner, box=blank_box, padding=(0, 0, 0, 0)),
        refresh_per_second=100,
        console=console,
        transient=False,
    )
    new_live.start()
    time.sleep(3)
    console.print(Padding("Done processing", (1, 0, 0, 1)))
    new_live.update("")
    new_live.stop()


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


if __name__ == "__main__":
    # Welcome screen and (intial settings via arrow keys and toggle -> TODO)
    render_intro(console)
    last_keystroke = None

    # Common for threads and user inputs
    lock = threading.Lock()
    query_queue = SimpleQueue()
    stop_event = threading.Event()
    buffer = ""

    # Start background daemon thread for processing queries
    bg_processing_thread = threading.Thread(
        target=bg_query_processing,
        args=(buffer, stop_event, query_queue, console),
        daemon=True,
    )
    bg_processing_thread.start()

    command_bar = Live(
        render_command_bar(buffer),
        refresh_per_second=100,
        console=console,
        transient=False,
    )

    command_bar.start()

    try:
        while True:
            with GetchRaw() as getch:
                while True:
                    try:
                        char = read_keystroke(getch.fd)
                        if not char:
                            continue

                        # Ignore arrow keys and TODO add other non-printable sequences that might not be required
                        if len(char) > 1 or char.startswith("\x1b"):
                            continue

                        last_keystroke = ord(char)

                        # --- Process user's query on `Enter` keystroke ---
                        if char == "\n" and len(buffer) > 0 and buffer[-1] != "\n":
                            query_queue.put(buffer)
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

                        # Show list of available commands
                        if char == "/" and len(buffer) == 1:
                            if not query_queue.empty():
                                command_bar.update(
                                    render_command_bar(
                                        render_alert="Cannot use / (commands) until your queries have been processed",
                                    )
                                )
                                continue

                            else:
                                command_bar.update(
                                    render_command_bar(
                                        "",
                                        True,
                                    )
                                )
                                command_bar.stop()
                                selected_command = show_commands()

                                if selected_command:
                                    buffer += selected_command

                                command_bar.start()

                        command_bar.update(render_command_bar(buffer, True))

                    except KeyboardInterrupt:
                        last_keystroke = ord("\x03")  # Ctrl + C
                        stop_event.set()
                        break

            # `Ctrl + C` keystroke
            if last_keystroke == 3:
                break

            # render_buffer = buffer
            # command_bar.update(render_command_bar(render_buffer, False))
            # command_bar.update("")

            # command_bar.stop()
            # invoke_agent(command_bar, render_buffer)
            # command_bar.start()

            # Reset and clear buffer
            buffer = ""
            command_bar.update(render_command_bar(buffer, False))

    finally:
        command_bar.stop()
        console.print(Padding("See you soon!", (0, 0, 1, 2)))
