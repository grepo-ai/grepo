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
from rich.tree import Tree
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
        # self.blank_box = Box("    \n" * 8, ascii=True)
        self.lock = lock
        self._previous_buffer = ""
        self.output_queue = output_queue
        self._log_history = ""
        self._renderable_data = self._default_stats()
        self.console = Console()
        self._thinking = False
        self._compaction = False
        self._commands_palette_active = False
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

        self._footer_split_panel = self._footer_panel(init=True)

    def _default_stats(self):
        stats_dict = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "session_cost": 0,
        }
        return stats_dict

    def _footer_panel(self, partial_render=False, init=False, blank=False, **kwargs):
        footer_tbl = Table.grid(expand=True)
        footer_tbl.add_column("", ratio=3)
        footer_tbl.add_column("", ratio=1, justify="right", no_wrap=True)
        footer_tbl.add_column("", ratio=1, justify="right", no_wrap=True)

        if init or blank:
            panel = Panel(
                footer_tbl,
                box=SIMPLE,
                height=0,
                padding=(0, 1, 0, 1),
            )

            return panel

        if self._commands_palette_active:
            if kwargs.get("list_all_commands"):
                return Commands.main_commands_selector()

            if kwargs.get("dynamic_selection", None) is not None:
                return Commands.main_commands_selector(kwargs["dynamic_selection"])

        elif partial_render:
            if self._thinking:
                left_text = "[dim]Press / for commands (coming soon) • Ctrl-C (quit)[/]"
                right_text = "[#B6CBFA]Thinking on[/] [dim](tab to toggle)[/]"
            else:
                left_text = "[dim]Press / for commands (coming soon) • Ctrl-C (quit)[/]"
                right_text = "[dim]Thinking off (tab to toggle)[/]"

            if self._compaction:
                footer_tbl.add_row(
                    f"{left_text}",
                    Spinner(
                        "dots3",
                        text="[#FCE2B3]compacting context[/]",
                        style="#FCE2B3",
                    ),
                    f"{right_text}",
                )
            else:
                footer_tbl.add_row(f"{left_text}", "", f"{right_text}")

            return footer_tbl

        else:
            left_text = "[dim]Press / for commands (coming soon) • Ctrl-C (quit)[/]"
            right_text = "[dim]Thinking off (tab to toggle)[/]"

            footer_tbl.add_row(
                f"{left_text}",
                "",
                f"{right_text}",
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

    def update_spinner(
        self,
        spin_it: bool = True,
        status_text: str = None,
        data: str = None,
    ):
        status_fillers = ["Jellying...", "Chewing GPUs...", "Poking intelligence..."]

        if not status_text:
            status_text = random.choice(status_fillers)

        if spin_it:
            self.spinner.renderable = Spinner(
                "dots", text=f"[#FC814C]{status_text}[/]", style="#FC814C"
            )

        elif not spin_it and data is not None:
            self.spinner.renderable = data

        else:
            self.spinner.renderable = (
                "[#969696]Let me know what else you need help with.[/]"
            )

    def update_footer_split(self, blank=False, **kwargs):
        if kwargs.get("list_all_commands", None) is not None:
            self._footer_split_panel.renderable = self._footer_panel(
                list_all_commands=kwargs.get("list_all_commands")
            )
            self._footer_split_panel.height = 8

        elif kwargs.get("dynamic_selection", None) is not None:
            self._footer_split_panel.renderable = self._footer_panel(
                dynamic_selection=kwargs.get("dynamic_selection")
            )
            self._footer_split_panel.height = 8

        elif kwargs.get("thinking", None) is not None:
            self._thinking = kwargs.get("thinking")
            self._footer_split_panel.renderable = self._footer_panel(
                partial_render=True
            )

        elif kwargs.get("compaction", None) is not None:
            self._compaction = kwargs.get("compaction")
            self._footer_split_panel.renderable = self._footer_panel(
                partial_render=True
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
            self._footer_split_panel = self._footer_panel(blank=True)

    def __rich__(self):
        # Only render the rest of the panels as agent logs are printed directly above Live region via console.print()
        return Group(
            # self._upper_split_panel,
            self.spinner,
            self._lower_split_panel,
            self._footer_split_panel,
        )


@dataclass(slots=True)
class TreeRender:
    """
    This dataclass is used for managing lifecycle of rich tree objects
    as well as for rendering tool calls generated data as tree objects.
    """

    node_map: dict[int, set[str]] = field(default_factory=dict)

    def build_tree(self, name):
        tree_map = {
            "grep": Tree("[#FAFAFA]● [/][#7CFCA7]Search[/]"),
            "list": Tree("[#FAFAFA]● [/][#7CFCA7]List[/]"),
            "read": Tree("[#FAFAFA]● [/][#7CFCA7]Read[/]"),
            "write": Tree("[#FAFAFA]● [/][#7CFCA7]Write[/]"),
            "code_block": Tree("[#FAFAFA]● [/][#7CFCA7]Code Search[/]"),
            "glob": Tree("[#FAFAFA]● [/][#7CFCA7]Glob[/]"),
            "edit": Tree("[#FAFAFA]● [/][#7CFCA7]Edit[/]"),
        }

        return tree_map.get(name)

    def add_leaf(self, tree_type: Tree, values: list):
        if id(tree_type) not in self.node_map:
            self.node_map[id(tree_type)] = set()

        for val in values:
            if val in self.node_map[id(tree_type)]:
                continue
            self.node_map[id(tree_type)].add(val)
            tree_type.add(val)


if __name__ == "__main__":
    import time

    console = Console()

    tree_render = TreeRender()
    grep_tree = tree_render.build_tree(name="grep")
    paths = ["/src/agent/main.py", "/src/cli/main.py", "/src/agent/tools.py"]

    tree_render.add_leaf(grep_tree, values=paths)
    console.print(grep_tree)

    time.sleep(2)

    new_path = ["/src/cli/mains.py"]
    tree_render.add_leaf(grep_tree, values=new_path)
    console.print(grep_tree)
