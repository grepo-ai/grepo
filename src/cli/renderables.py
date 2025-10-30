import os
from dataclasses import dataclass, field
import pyfiglet
import random
from typing import Any, Union


from rich.console import Console, ConsoleOptions, Group, RenderResult
from rich.text import Text
from rich.panel import Panel
from rich.box import Box
from rich.box import SIMPLE, ASCII2
from rich.spinner import Spinner
from rich.table import Table
from rich.tree import Tree
from cli.commands import Commands
from cli.utils import color_palette


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
    # Grepo logo
    text = Text()
    text.append(pyfiglet.figlet_format("grepo", font="ansi_shadow"))

    # Root directory and help or / commands info
    init_lines = f"[#60FCF5]{text}[/]\n[{color_palette.get('intro-text-pink')}] cwd: {os.getcwd()}\n\n[italic] /help for help, / for list of commands[/]\n[#60FCF5] {'─' * 39}[/]"
    console.print(
        Panel(
            init_lines,
            box=SIMPLE,
            padding=(0, 0, 0, 1),
        )
    )


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
    def __init__(self, output_queue, lock, console):
        # self.blank_box = Box("    \n" * 8, ascii=True)
        self.lock = lock
        self.output_queue = output_queue
        self._log_history = ""
        self._renderable_data = self._default_stats()
        self.console = console
        self._thinking = False
        self._compaction = False
        self._commands_palette_active = False
        self._lower_split_panel = self._lower_panel(init=True, screen_type="init")
        self.spinner = Panel(
            "[#969696]* Tip: Add AGENTS.md file in root dir of your project with your custom instructions, style guide or project architecture details.[/]",
            box=SIMPLE,
            height=0,
            padding=(0, 1, 0, 1),
        )
        self._footer_split_panel = self._footer_panel(init=True)
        # self._agent_logs = AgentLogs()  # Deprecated

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
                        text="[#B6CBFA]compacting context[/]",
                        style="#B6CBFA",
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

    def _lower_panel(
        self, main=False, init=False, render=True, screen_type=None, **kwargs
    ):
        # Main screen
        if main:
            panel = Panel(
                '[#69FFB4]> [dim]Try this "explain what this repo is about?" [/dim][/]',
                box=NO_SIDE_BORDER_BOX,
                border_style="#545454",
                height=3,
                width=self.console.size.width,
                padding=(0, 1, 0, 1),
            )

            return panel

        # Initial LLM selection and API input screen
        elif init and screen_type == "init":
            renderable_text = Commands.init_commands_selector(screen_type=screen_type)

            panel = Panel(
                renderable_text,
                box=ASCII2,
                height=8,
                width=100,
                padding=(1, 1, 0, 1),
            )

            return panel

        elif render:
            if kwargs.get("dynamic_selection") is not None:
                renderable_text = Commands.init_commands_selector(
                    dynamic_selection=kwargs.get("dynamic_selection"),
                    screen_type=screen_type,
                )

                height = 8
                border_style = None

            elif kwargs.get("recursive_render"):
                renderable_text = Commands.init_commands_selector(
                    screen_type=screen_type
                )
                height = 8
                border_style = None

            elif kwargs.get("clear_screen", False):
                renderable_text = "[dim]enter your API key[/]"
                height = 3
                border_style = None

            else:
                renderable_text, border_style = Commands.input_render_styles(
                    kwargs.get("buffer"),
                    kwargs.get("is_first_time"),
                    kwargs.get("render_alert"),
                )
                height = 3

            return renderable_text, border_style, height

    @property
    def renderable_data(self):
        return self._renderable_data

    @renderable_data.setter
    def renderable_data(self, data_dict):
        self._renderable_data = data_dict

    def update_lower_split(
        self,
        main=False,
        render=True,
        screen_type=None,
        **kwargs,
    ):
        if main:
            self._lower_split_panel = self._lower_panel(
                main=True, screen_type=screen_type
            )

        elif render:
            renderable_text, border_style, height = self._lower_panel(
                screen_type=screen_type, **kwargs
            )

            self._lower_split_panel.renderable = renderable_text

            if border_style is not None:
                self._lower_split_panel.border_style = border_style

            self._lower_split_panel.height = height

            if kwargs.get("clear_screen") is not None:
                self._lower_split_panel.width = 150
            # Update box style when transitioning to input mode
            if kwargs.get("clear_screen"):
                self._lower_split_panel.padding = (0, 1, 0, 1)

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
                "dots", text=f"[#60FCF5]{status_text}[/]", style="#60FCF5"
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

    node_map: dict[str, tuple[Tree, set[Union[str, int]]]] = field(default_factory=dict)

    def build_tree(self, id, name, data=None):
        tree_map = {
            "grep": Tree(f"[#FC69FF]● [/][#7AFF85][bold]Search[/bold][/] ({data})"),
            "list": Tree(f"[#FC69FF]● [/][#7AFF85][bold]List[/bold][/] ({data})"),
            "read": Tree("[#FC69FF]● [/][#7AFF85][bold]Read[/bold][/]"),
            "write": Tree(f"[#FC69FF]● [/][#7AFF85]Write[/] ({data})"),
            "code_search": Tree(
                f"[#FC69FF]● [/][#7AFF85][bold]Code Search[/bold][/] ({data})"
            ),
            "glob": Tree(f"[#FC69FF]● [/][#7AFF85][bold]Glob[/bold][/] ({data})"),
            "edit": Tree(f"[#FC69FF]● [/][#7AFF85][bold]Edit[/bold][/] ({data})"),
            "tree": Tree(f"{data}[/]"),
        }

        self.node_map[id] = (tree_map.get(name), set())

    def get_tree(self, id: str):
        if id in self.node_map:
            return self.node_map.get(id)[0]

    def get_tree_leafs(self, id):
        if id in self.node_map:
            return self.node_map.get(id)[1]

    def add_leaf(self, id: str, values: list | str):
        if id not in self.node_map:
            raise ValueError("Tree does not exist")

        if isinstance(values, str):
            if values in self.node_map[id][1]:
                return

            # Add to Tree object
            self.node_map[id][0].add(values)
            # Add to set
            self.node_map[id][1].add(values)

        else:
            for val in values:
                if isinstance(val, tuple):
                    if val[0] in self.node_map[id][1]:
                        continue

                    # Add to Tree object
                    self.node_map[id][0].add(val[1])
                    # Add to set
                    self.node_map[id][1].add(val[0])

                else:
                    if val in self.node_map[id][1]:
                        continue

                    # Add to Tree object
                    self.node_map[id][0].add(val)
                    # Add to set
                    self.node_map[id][1].add(val)


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
