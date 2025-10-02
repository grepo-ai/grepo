import os
from dataclasses import dataclass, field
import pyfiglet
import random
from typing import Any


from rich.console import Console, ConsoleOptions, Group
from rich.text import Text
from rich.panel import Panel
from rich.box import Box
from rich.box import ROUNDED, SIMPLE
from rich.spinner import Spinner
from src.cli.commands import Commands


def render_intro(console):
    console.print("\n")
    text = Text()
    text.append(pyfiglet.figlet_format("grepo", font="ansishadow"), style="#8FF4FF")
    console.print(text)

    panel = Panel(
        f"[#FAFAFA]   * Welcome to [#80FFFD]Grepo[/] * [/] \n\n [#F5BE3D]  cwd: {os.getcwd()}[/] \n\n  [#F5BE3D] [italic]type /help for help[/italic],[italic] / for list of commands[/] ",
        box=ROUNDED,
        border_style="#80FFFD",
        expand=False,
        padding=(0, 0, 0, 0),
    )
    console.print(panel)


def input_render_styles(buffer=None, is_first_time=True, render_alert=None):
    # Render any alerts
    if render_alert:
        renderable_text = f"[#FF6969]> {render_alert}[/]"
        border_style = "#FF6969"

    # Empty buffer shows placeholder text
    elif not buffer and is_first_time:
        renderable_text = (
            '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]'
        )
        border_style = "#69FFB4"

    # Bash command buffer style
    elif buffer and buffer[0] == "#":
        buffer = buffer[1:]
        renderable_text = f"[#FFD66E]# {buffer}_[/]"
        border_style = "#FFD66E"

    # Default input bar style
    else:
        renderable_text = f"[#69FFB4]> {buffer}_[/]"
        border_style = "#69FFB4"

    return renderable_text, border_style


@dataclass
class AgentLogs:
    messages: list[Any] = field(default_factory=list)
    rendered_all_once: bool = False

    def add(self, message):
        self.messages.append(message)
        # self.rendered_all_once = False
        # if len(self.messages) >= 5:
        #     self.messages = self.messages[3:]

    def clear(self):
        self.messages.clear()

    def __rich_console__(self, console: Console, options: ConsoleOptions):
        # if not self.rendered_all_once:
        for message in self.messages:
            yield message
            # self.rendered_all_once = True


class RenderSplits:
    def __init__(self, output_queue, lock):
        self.blank_box = Box("    \n" * 8, ascii=True)
        self.lock = lock
        self._previous_buffer = ""
        self.output_queue = output_queue
        self._log_history = ""
        self._renderable_data = {}
        self.console = Console()
        self._agent_logs = AgentLogs()

        self._upper_split_panel = Panel(
            self._agent_logs,
            box=SIMPLE,
            # height=30,
        )
        self._lower_split_panel = Panel(
            '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]',
            box=ROUNDED,
            border_style="#545454",
            height=3,
        )
        self.spinner = Panel(
            "[#969696]* Tip: Add .greporules for custom instructions for Grepo to remember[/]",
            box=SIMPLE,
            height=0,
        )

        self._footer_split_panel = Panel(
            "[dim]Press ? for shortcuts[/]", box=SIMPLE, height=0
        )

    @property
    def renderable_data(self):
        return self._renderable_data

    @renderable_data.setter
    def renderable_data(self, data_dict):
        self._renderable_data = data_dict

    def update_upper_split(self, renderable_data=None, **kwargs):
        if renderable_data:
            self._upper_split_panel.renderable = renderable_data

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

    def update_spinner(self, spin_it=True, status_text=None):
        status_fillers = ["Jellying...", "Chewing GPUs...", "Poking intelligence..."]

        if not status_text:
            status_text = random.choice(status_fillers)

        if spin_it:
            self.spinner.renderable = Spinner(
                "star", text=f"[#FFB82B]{status_text}[/]", style="#FFB82B"
            )
        else:
            self.spinner.renderable = (
                "[#969696]Let me know what else you need help with.[/]"
            )

    def update_footer_split(self, blank=False, **kwargs):
        dynamic_selection = kwargs.get("dynamic_selection", None)
        list_all_commands = kwargs.get("list_all_commands", False)
        exit_screen = kwargs.get("exit_screen", False)

        if list_all_commands:
            self._footer_split_panel.renderable = Commands.main_commands_selector()
            self._footer_split_panel.height = 8

        elif dynamic_selection is not None:
            self._footer_split_panel.renderable = Commands.main_commands_selector(
                dynamic_selection
            )
            self._footer_split_panel.height = 8

        elif exit_screen:
            render_data = ""
            token_usage_keys = {
                "total_input_tokens": "Total Input Tokens",
                "total_output_tokens": "Total Output Tokens",
                "cache_creation_input_tokens": "Cache Write Tokens",
                "cache_read_input_tokens": "Cache Read Tokens",
                "session_cost": "Total Cost ($)",
            }

            if self.renderable_data:
                for key, value in self.renderable_data.items():
                    if key == "context_window_used":
                        continue
                    render_data += f"{token_usage_keys.get(key)}: {value}\n"

            if render_data:
                self._footer_split_panel.renderable = (
                    f"[#F47AFF][dim]{render_data}[/][/]"
                )
                self._footer_split_panel.box = ROUNDED
                self._footer_split_panel.title = "Session Stats"
                self._footer_split_panel.border_style = "#8FF4FF"
                self._footer_split_panel.style = "dim"
                self._footer_split_panel.height = 7

        elif blank:
            self._footer_split_panel.renderable = "[dim]Press ? for shortcuts[/]"
            self._footer_split_panel.height = 0

    def __rich__(self):
        return Group(
            self._upper_split_panel,
            self.spinner,
            self._lower_split_panel,
            self._footer_split_panel,
        )
