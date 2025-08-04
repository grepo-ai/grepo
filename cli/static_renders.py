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


def render_intro(console):
    print("\n")
    text = Text()
    text.append(pyfiglet.figlet_format("grepo", font="ansishadow"), style="#8FA9FF")
    console.print(text)

    table = Table()
    table.add_column("url")

    panel = Panel(
        f"[#FAFAFA]   * Welcome to [#ABCAFF]Grepo[/] * [/] \n\n [#969696]  cwd: {os.getcwd()}[#969696] \n\n   [italic]type /help for help[/italic],[italic] / for list of commands[/] ",
        box=HEAVY_EDGE,
        border_style="#A8C0FF",
        expand=False,
        padding=(0, 0, 0, 0),
    )
    console.print(panel)


def render_command_bar(buffer=None, is_first_time=True, render_alert=None):
    # Render any alerts
    if render_alert:
        renderable_text = f"[#FF6969]> {render_alert}[/]"
        border_style = "#545454"

    # Empty buffer shows placeholder text
    elif not buffer and is_first_time:
        renderable_text = (
            '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]'
        )
        border_style = "#545454"

    # Bash command buffer style
    elif buffer and buffer[0] == "#":
        buffer = buffer[1:]
        renderable_text = f"[#FFD66E]# {buffer}_[/]"
        border_style = "#FFD66E"

    # Default input bar style
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
