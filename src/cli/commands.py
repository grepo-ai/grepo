from typing import Optional
from cli.terminal import read_keystroke


class Commands:
    AVAILABLE_MAIN_COMMANDS = ["help", "config", "ask"]
    INIT_SCREEN_COMMANDS = [
        {
            "Select AI model": [
                "Anthropic Sonnet 4.5",
                "Anthropic Sonnet 4",
                "Anthropic Haiku 4.5",
            ]
        },
        {"hello": ["abc"]},
        {"sure": ["why not"]},
    ]

    def __init__(self, console=None, rendered_regions=None):
        self.console = console
        self.rendered_commands_region = rendered_regions
        self._buffer = ""

    def show(self, type="MAIN", render_region: Optional[str] = None):
        dynamic_selection = -1

        while True:
            char = read_keystroke()

            if not char:
                continue

            # Main commands
            if render_region == "footer":
                if char == "\x1b":  # ESC key
                    selected_command = ""
                    return selected_command

                elif char == "\x1b[B":  # DOWN arrow
                    dynamic_selection += 1

                elif char == "\x1b[A":  # UP arrow
                    dynamic_selection -= 1

                self.rendered_commands_region.update_footer_split(
                    dynamic_selection=dynamic_selection
                )

                dynamic_selection = dynamic_selection % len(
                    self.__class__.AVAILABLE_MAIN_COMMANDS
                )

            # Init commands
            if render_region == "lower":
                if char == "\x1b":  # ESC key
                    selected_command = ""
                    return selected_command

                if char == "\x1b[B":  # DOWN arrow
                    dynamic_selection += 1

                elif char == "\x1b[A":  # UP arrow
                    dynamic_selection -= 1

                self.rendered_commands_region.update_lower_split(
                    dynamic_selection=dynamic_selection
                )

                dynamic_selection = dynamic_selection % len(
                    self.__class__.INIT_SCREEN_COMMANDS
                )

            # Instead of passing to main buffer manage independent flows for each command in footer rendered region only
            # unless some command requires addition to main buffer something like : /add-dir
            # Select this command and pass it to main input buffer.

            # TODO: Current version on passes the selected option to main buffer but need to handle all edge cases

            if char == "\n":
                if render_region == "footer":
                    selected_command = self.__class__.AVAILABLE_MAIN_COMMANDS[
                        dynamic_selection
                    ]
                    return selected_command

                elif render_region == "lower":
                    selected_command = self.__class__.INIT_SCREEN_COMMANDS[
                        dynamic_selection
                    ]

                    return selected_command

            # TODO: Add support for more non-printable escape sequences that are not required to be processed
            # For all keystrokes except arrow keys just return the char and add to main buffer
            elif char not in ("\x1b[B", "\x1b[A", "\x1b[C", "\x1b[D", "\x7f"):
                return char

            elif char == "\x7f":  # `Backspace` keystroke
                return char[:-1]

    @staticmethod
    def main_commands_selector(dynamic_selection=None):
        commands = [
            "[dim] /help\n[/]",
            "[dim] /config\n[/]",
            "[dim] /ask\n[/]",
        ]

        if dynamic_selection is not None:
            dynamic_selection = dynamic_selection % 3

            command_index = commands[dynamic_selection].find("]")
            command = commands[dynamic_selection][command_index + 1 :]
            commands[dynamic_selection] = f"[#E896FF]{command[: command.find('[')]}[/]"

        selected_command = "".join(commands)

        return (
            selected_command
            + "[dim]\n Press ↑/↓ to move up/down • `Enter` to select • `Esc` to exit[/]"
        )

    @staticmethod
    def init_commands_selector(dynamic_selection=None):
        commands = [
            "[dim]• Select AI model\n[/]",
            "[dim]• Allow Grepo to edit files in this directory\n[/]",
            "[dim]• Ask for permission for file edits\n[/]",
        ]

        if dynamic_selection is not None:
            dynamic_selection = dynamic_selection % 3

            command_index = commands[dynamic_selection].find("]")
            command = commands[dynamic_selection][command_index + 1 :]
            commands[dynamic_selection] = (
                f"[#BDFF99]> {command[2 : command.find('[')]}[/]"
            )

        selected_command = "".join(commands)

        return (
            selected_command
            + "[dim]\n Press ↑/↓ to move up/down • `Enter` to select • `Esc` to exit this setup[/]"
        )

    @staticmethod
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
