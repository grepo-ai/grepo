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

from src.cli import render_intro, render_command_bar, render_commands_list, GetchRaw
import threading
from queue import SimpleQueue


console = Console()
blank_box = Box("    \n" * 8, ascii=True)
all_commands = ["help", "settings", "search"]


# Read keystrokes
def read_keystroke(fd):
    # tty.setraw(fd) # WOW read why this loc infinite glitched the live refresh panel everytime i keystroked

    rlist, _, _ = select.select([sys.stdin], [], [], 0.02)

    if not rlist:
        return None

    # Read first byte
    ch = sys.stdin.read(1)

    # Return normal keystrokes
    if ch != "\x1b":
        return ch

    # So we handled normal keystrokes now we know it is possibly an arrow sequence
    # (arrow keys are sequence of multiple bytes)
    # so we need to record that sequence (multi-byte) over a time range to make it look like single
    # logical key i.e arrow

    arrow_key_seq = ch

    seq_time_range = time.monotonic() + 0.05
    while time.monotonic() < seq_time_range:
        rlist, _, _ = select.select([sys.stdin], [], [], 0.01)

        next_char = sys.stdin.read(1)

        if not next_char:
            break

        arrow_key_seq += next_char
        if arrow_key_seq in ("\x1b[B", "\x1b[A"):
            break
        if len(arrow_key_seq) == 6:
            break
    return arrow_key_seq


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


if __name__ == "__main__":
    # Welcome screen and (intial settings via arrow keys and toggle -> TODO)
    render_intro(console)

    buffer = ""
    last_keystroke = None

    command_bar = Live(
        render_command_bar(buffer),
        refresh_per_second=100,
        console=console,
        transient=False,
    )

    # Live session started
    command_bar.start()

    # Common data store for threads and user inputs
    buffer_data = ""
    lock = threading.Lock()
    query_queue = SimpleQueue()

    try:
        while True:
            with GetchRaw() as getch:
                while True:
                    try:
                        char = read_keystroke(getch.fd)
                        if not char:
                            continue

                        last_keystroke = ord(char)

                        if (
                            char == "\n" and len(buffer) > 0 and buffer[-1] != "\n"
                        ):  # `Enter` keystroke i.e run the input query
                            break
                        elif char == "\x7f":  # `Backspace` keystroke
                            buffer = buffer[:-1]

                        else:
                            if (
                                not buffer and char == "\n"
                            ):  # Handle repeated `Enter` keystrokes
                                continue
                            else:
                                buffer += char

                        if char == "/" and len(buffer) == 1:
                            command_bar.update(render_command_bar(buffer, True))
                            command_bar.stop()
                            selected_command = show_commands()

                            if selected_command:
                                buffer += selected_command

                            command_bar.start()

                        command_bar.update(render_command_bar(buffer, True))

                    except KeyboardInterrupt:
                        last_keystroke = ord("\x03")  # Ctrl + C
                        break

            # `ctrl-c` keystroke
            if last_keystroke == 3:
                break

            render_buffer = buffer
            command_bar.update(render_command_bar(render_buffer, False))
            command_bar.update("")

            command_bar.stop()
            invoke_agent(command_bar, render_buffer)
            command_bar.start()

            # Reset and clear buffer
            buffer = ""
            command_bar.update(render_command_bar(buffer, False))

    finally:
        command_bar.stop()
        console.print(Padding("See you soon!", (0, 0, 1, 2)))
