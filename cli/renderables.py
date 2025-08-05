import os
from rich.console import Group
from rich.text import Text
from rich.panel import Panel
from rich.box import HEAVY_EDGE, ROUNDED, SIMPLE
from rich.spinner import Spinner
import pyfiglet
import random


def render_intro(console):
    console.print("\n")
    text = Text()
    text.append(pyfiglet.figlet_format("grepo", font="ansishadow"), style="#8FA9FF")
    console.print(text)

    panel = Panel(
        f"[#FAFAFA]   * Welcome to [#ABCAFF]Grepo[/] * [/] \n\n [#969696]  cwd: {os.getcwd()}[/] \n\n   [italic]type /help for help[/italic],[italic] / for list of commands[/] ",
        box=HEAVY_EDGE,
        border_style="#A8C0FF",
        expand=False,
        padding=(0, 0, 0, 0),
    )
    console.print(panel)


def input_render_styles(buffer=None, is_first_time=True, render_alert=None):
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

    return renderable_text, border_style


class RenderSplits:
    def __init__(self, output_queue, blank_box):
        self._last_log_count = 0
        self._previous_buffer = ""
        self.output_queue = output_queue
        self._upper_split_panel = Panel(
            "[#F35CFF]How can i help you today?[/]",
            box=SIMPLE,
            height=0,
        )
        self._lower_split_panel = Panel(
            '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]',
            box=ROUNDED,
            border_style="#545454",
            height=3,
        )
        self.spinner = Panel(
            "[#969696]* Tip: Add .greporules for custome instructions for Grepo to remember[/]",
            box=SIMPLE,
            height=0,
        )

    def update_upper_split(self):
        if self.output_queue and len(self.output_queue) != self._last_log_count:
            render_logs = "\n".join(self.output_queue)
            self._upper_split_panel.renderable = f"[#CFCFCF]{render_logs}[/]"
            # TODO add dynamic re-sizing and auto-scrolling logic
            self._upper_split_panel.height = 5

            # Update last log count this is done to avoid frequent updates when no new logs arrived
            self._last_log_count = len(self.output_queue)

    def update_lower_split(
        self, console, buffer, is_first_time=True, render_alert=False
    ):
        renderable_text, border_style = input_render_styles(
            buffer, is_first_time, render_alert
        )

        self._lower_split_panel.renderable = renderable_text
        self._lower_split_panel.border_style = border_style

        # This is to prevent frequent updates when buffer didnt even change
        self._previous_buffer = buffer

    def update_spinner(self, status_text=None):
        status_fillers = ["Thinking hard like jelly...", "Chewing GPUs..."]

        if not status_text:
            status_text = random.choice(status_fillers)

        self.spinner.renderable = Spinner(
            "star", text=f"[#FFC375]{status_text}[/]", style="#FFC375"
        )

    def __rich__(self):
        return Group(self._upper_split_panel, self.spinner, self._lower_split_panel)
