from rich.panel import Panel


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
