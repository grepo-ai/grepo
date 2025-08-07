from cli.terminal import read_keystroke


class Commands:
    AVAILABLE_MAIN_COMMANDS = ["help", "config", "ask"]

    def __init__(self, console=None, rendered_regions=None):
        self.console = console
        self.rendered_commands_region = rendered_regions

    def show(self, type="MAIN"):
        dynamic_selection = -1

        while True:
            char = read_keystroke()

            if not char:
                continue

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

            # TODO: Instead of passing to main buffer manage independent flows for each command in footer rendered region only
            # unless some command requires addition to main buffer something like : /add-dir
            # Select this command and pass it to main input buffer

            dynamic_selection = dynamic_selection % 3

            if char == "\n":
                selected_command = self.__class__.AVAILABLE_MAIN_COMMANDS[
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
