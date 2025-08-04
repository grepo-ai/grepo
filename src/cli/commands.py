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


def render_commands_list(blank_box, dynamic_selection=None):
    commands = ["[dim]/help\n[/]", "[dim]/settings\n[/]", "[dim]/search\n[/]"]

    if dynamic_selection is not None:
        if dynamic_selection < 0:
            dynamic_selection += 1

        command_index = commands[dynamic_selection].find("/")
        command = commands[dynamic_selection][command_index:]
        commands[dynamic_selection] = command[: command.find("[")]

    render_selected_command = "".join(commands)

    return Panel(render_selected_command, box=blank_box, padding=(0, 0, 0, 2))
