import os
from dataclasses import dataclass, field
import pyfiglet
import random
from typing import Any


from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.text import Text
from rich.panel import Panel
from rich.box import Box
from rich.box import SIMPLE
from rich.spinner import Spinner
from rich.padding import Padding
from rich.table import Table
from src.cli.commands import Commands
from src.cli.utils import color_palette


# Custom box with no left/right borders (only top and bottom horizontal lines)
NO_SIDE_BORDER_BOX = Box(
    " ── \n"  # top: space, horizontal, horizontal, space
    "    \n"  # head: 4 spaces
    " ── \n"  # head divider
    "    \n"  # mid: 4 spaces
    " ── \n"  # mid divider
    " ── \n"  # row divider
    "    \n"  # foot: 4 spaces
    " ── \n"  # bottom: space, horizontal, horizontal, space
)


def render_intro(console):
    console.print("\n\n")
    text = Text()
    text.append(pyfiglet.figlet_format("grepo", font="ansishadow"), style="#8FF4FF")
    console.print(text)

    console.print(f"[{color_palette.get('intro-text-pink')}] cwd: {os.getcwd()}[/]\n")
    console.print(
        f"[{color_palette.get('intro-text-pink')}][italic] /help for help[/italic],[italic] / for list of commands[/]"
    )
    console.print(
        Padding(Text("─" * 40, style=color_palette.get("cyan")), (0, 0, 0, 1))
    )


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


# Deprecated: (only kept for reference)
@dataclass
class AgentLogs:
    messages: list[Any] = field(default_factory=list)
    rendered_all_once: bool = False
    _version: int = 0  # Internal version counter to trigger re-renders

    def add(self, message):
        self.messages.append(message)
        self._version += 1  # Increment to trigger Live refresh

    def clear(self):
        self.messages.clear()
        self._version += 1

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        """Render all messages - content will be clipped by panel's max_height"""
        if not self.messages:
            return

        # Yield all messages in order
        for message in self.messages:
            yield message


class RenderSplits:
    def __init__(self, output_queue, lock):
        self.blank_box = Box("    \n" * 8, ascii=True)
        self.lock = lock
        self._previous_buffer = ""
        self.output_queue = output_queue
        self._log_history = ""
        self._renderable_data = self._default_stats()
        self.console = Console()
        # self._agent_logs = AgentLogs()  # Deprecated

        # self._upper_split_panel = Panel(
        #     self._agent_logs,
        #     box=SIMPLE,
        # )

        self._lower_split_panel = Panel(
            '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]',
            box=NO_SIDE_BORDER_BOX,
            border_style="#545454",
            height=3,
            padding=(0, 1, 0, 1),
        )

        self.spinner = Panel(
            "[#969696]* Tip: Add AGENTS.md file in root dir of your project with your custom instructions, style guide or project architecture details.[/]",
            box=SIMPLE,
            height=0,
            padding=(0, 1, 0, 1),
        )

        self._footer_split_panel = self._footer_panel()

    def _default_stats(self):
        stats_dict = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "session_cost": 0.0,
        }
        return stats_dict

    def _footer_panel(self, partial_render=False, **kwargs):
        if partial_render:
            if kwargs.get("thinking", False):
                left_text = "[dim]Press / for commands (coming soon) • Ctrl-C (quit)[/]"
                right_text = "[#B6CBFA]Thinking on (tab to toggle)[/]"
            else:
                left_text = "[dim]Press / for commands (coming soon) • Ctrl-C (quit)[/]"
                right_text = "[dim]Thinking off (tab to toggle)[/]"

            footer_tbl = Table.grid(expand=True)
            footer_tbl.add_column("", ratio=3)
            footer_tbl.add_column("", ratio=1, justify="right", no_wrap=True)
            footer_tbl.add_row(f"{left_text}", f"{right_text}")

            return footer_tbl

        else:
            left_text = "[dim]Press / for commands (coming soon) • Ctrl-C (quit)[/]"
            right_text = "[dim]Thinking off (tab to toggle)[/]"

        footer_tbl = Table.grid(expand=True)
        footer_tbl.add_column("", ratio=3)
        footer_tbl.add_column("", ratio=1, justify="right", no_wrap=True)

        footer_tbl.add_row(f"{left_text}", f"{right_text}")

        panel = Panel(
            footer_tbl,
            box=SIMPLE,
            height=0,
            padding=(0, 1, 0, 1),
        )
        return panel

    @property
    def renderable_data(self):
        return self._renderable_data

    @renderable_data.setter
    def renderable_data(self, data_dict):
        self._renderable_data = data_dict

    # def update_upper_split(self, renderable_data=None, **kwargs):
    #     if renderable_data:
    #         self._upper_split_panel.renderable = renderable_data

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

    def update_spinner(self, spin_it=True, status_text=None, data: str = None):
        status_fillers = ["Jellying...", "Chewing GPUs...", "Poking intelligence..."]

        if not status_text:
            status_text = random.choice(status_fillers)

        if spin_it:
            self.spinner.renderable = Spinner(
                "star", text=f"[#F27F4E]{status_text}[/]", style="#F27F4E"
            )

        elif not spin_it and data is not None:
            self.spinner.renderable = data

        else:
            self.spinner.renderable = (
                "[#969696]Let me know what else you need help with.[/]"
            )

    def update_footer_split(self, blank=False, **kwargs):
        if kwargs.get("list_all_commands", False):
            self._footer_split_panel.renderable = Commands.main_commands_selector()
            self._footer_split_panel.height = 8

        elif kwargs.get("dynamic_selection", None) is not None:
            self._footer_split_panel.renderable = Commands.main_commands_selector(
                kwargs["dynamic_selection"]
            )
            self._footer_split_panel.height = 8

        elif kwargs.get("thinking", None) is not None:
            self._footer_split_panel.renderable = self._footer_panel(
                partial_render=True, thinking=kwargs["thinking"]
            )

        elif kwargs.get("exit_screen", False):
            stats_tbl = Table.grid(expand=False)
            stats_tbl.add_column(
                "", no_wrap=True, width=20
            )  # width is used to add space between column values for each row
            stats_tbl.add_column("", justify="left")

            token_usage_keys = {
                "total_input_tokens": "Total input tokens",
                "total_output_tokens": "Total output tokens",
                "cache_creation_input_tokens": "Cache write",
                "cache_read_input_tokens": "Cache read",
                "session_cost": "Total cost ($)",
                "model_used": "Models used",
            }

            for key, value in self.renderable_data.items():
                if key == "context_window_used":
                    continue
                stats_tbl.add_row(token_usage_keys.get(key), str(value))

            self._footer_split_panel.renderable = stats_tbl
            self._footer_split_panel.box = SIMPLE
            self._footer_split_panel.style = "dim"
            self._footer_split_panel.height = 7

        elif blank:
            self._footer_split_panel = self._footer_panel()

    def __rich__(self):
        # Only render the rest of the panels as agent logs are printed directly above Live region via console.print()
        return Group(
            # self._upper_split_panel,
            self.spinner,
            self._lower_split_panel,
            self._footer_split_panel,
        )
