import os
import sys
import termios
import tty
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


console = Console()
blank_box = Box("    \n" * 8, ascii=True)


def render_intro(console):
    print("\n")
    text = Text()
    text.append(pyfiglet.figlet_format("grepo", font="ansishadow"), style="#8FA9FF")
    console.print(text)

    table = Table()
    table.add_column("url")

    panel = Panel(
        f"[#FAFAFA] * Welcome to [#ABCAFF]Grepo[/] * [/] \n\n [#969696] cwd: {os.getcwd()}[#969696] \n\n [italic]type /help for help[/italic]",
        box=HEAVY_EDGE,
        border_style="#A8C0FF",
        expand=False,
    )
    console.print(panel)


def render_command_bar(buffer, is_first_time=True):
    # Empty buffer shows placeholder text
    if not buffer and is_first_time:
        renderable_text = (
            '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]'
        )
        border_style = "#545454"

    # Bash command buffer style
    elif buffer and buffer[0] == "#":
        buffer = buffer[1:]
        renderable_text = f"[#FFD66E]# {buffer}_[/]"
        border_style = "#FFD66E"

    # Default buffer style
    else:
        renderable_text = f"[#69FFB4]> {buffer}_[/]"
        border_style = "#545454"

    panel = Panel(
        renderable_text,
        box=ROUNDED,
        border_style=border_style,
        height=3,
    )
    return panel


# Read command inputs from terminal
def getch():
    fd = sys.stdin.fileno()
    old_attrs = termios.tcgetattr(fd)
    try:
        # tty.setraw(fd) # WOW read why this loc infinite glitched the live refresh panel everytime i keystroked
        tty.setcbreak(fd)
        ch = sys.stdin.read(1)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)
    return ch, ord(ch)


# TODO Try this approach spawn another Live region to manage
# toggle options and post selection return the selected option back to old live region
# and render the option in the `command bar`


def render_commands_list():
    command_list = "/help\n/settings\n/search\n/agent"
    return Panel(command_list, box=blank_box, padding=(0, 0, 1, 2))


def show_commands():
    import time

    live_commands = Live(
        render_commands_list(),
        refresh_per_second=100,
        console=console,
        transient=False,
    )
    live_commands.start()
    try:
        while True:
            time.sleep(3)
            live_commands.update(render_commands_list())

    finally:
        live_commands.stop()


def invoke_agent(buffer):
    console.print(Padding(f"[#ABABAB]> {buffer}[/]", (1, 0, 0, 2)))
    a = "Sure let me run this command and see what i can do!"
    console.print(Padding(a, (1, 0, 0, 2)))


if __name__ == "__main__":
    # Welcome screen and (intial settings via arrow keys and toggle -> TODO)
    render_intro(console)

    buffer = ""
    last_keystroke = None

    # Manual start/stop version
    command_bar = Live(
        render_command_bar(buffer),
        refresh_per_second=100,
        console=console,
        transient=False,
    )

    # Live session started
    command_bar.start()

    try:
        while True:
            while True:
                try:
                    char, ord_no = getch()
                    last_keystroke = ord_no

                    if (
                        char == "\n" and len(buffer) > 0 and buffer[-1] != "\n"
                    ):  # `Enter` keystroke
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
                        command_bar.stop()
                        show_commands()
                        # TODO fix bug command bar re-renders cause we are calling update right after it and
                        # it is refreshing reallly quickly so need to halt live region precicely
                        # and then render toggle menu below it and then resume live region again post selection from
                        # toggle menu
                        command_bar.start()

                    command_bar.update(render_command_bar(buffer, True))

                except KeyboardInterrupt:
                    last_keystroke = ord("\x03")  # Ctrl + C
                    break

            if last_keystroke == 3:
                break
            else:
                invoke_agent(buffer)

            # Reset and clear buffer
            buffer = ""
            command_bar.update(render_command_bar(buffer, False))
    finally:
        command_bar.stop()
        console.print(Padding("See you soon!", (1, 0, 1, 2)))
