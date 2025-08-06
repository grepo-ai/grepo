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

            if not char or char not in ("\x1b[A", "\x1b[B", "\x1b", "\n"):
                continue

            if char == "\x1b":  # ESC key
                selected_command = None
                break

            elif char == "\x1b[B":  # DOWN arrow
                dynamic_selection += 1

            elif char == "\x1b[A":  # UP arrow
                dynamic_selection -= 1

            self.rendered_commands_region.update_footer_split(
                dynamic_selection=dynamic_selection
            )

            # Select this command and pass it to main input buffer
            if char == "\n":
                if dynamic_selection < 0:
                    dynamic_selection += 1
                    selected_command = self.__class__.AVAILABLE_MAIN_COMMANDS[
                        dynamic_selection
                    ]
                    break

            # Reset values to avoid overflow
            if dynamic_selection == 2 or dynamic_selection == -4:
                dynamic_selection = -1

        return selected_command

    @staticmethod
    def main_commands_selector(dynamic_selection=None):
        commands = [
            "[dim] /help\n[/]",
            "[dim] /config\n[/]",
            "[dim] /ask\n[/]",
        ]

        if dynamic_selection is not None:
            if dynamic_selection < 0:
                dynamic_selection += 1

            command_index = commands[dynamic_selection].find("]")
            command = commands[dynamic_selection][command_index + 1 :]
            commands[dynamic_selection] = f"[#E896FF]{command[: command.find('[')]}[/]"

        selected_command = "".join(commands)

        return selected_command
