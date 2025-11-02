import sys
import os
import threading
from queue import SimpleQueue
from rich.console import Console
from rich.live import Live
from collections import deque


from agent.utils import generate_session_uuid, preprocess_dir
from cli.commands import Commands
from cli.terminal import GetchRaw, read_keystroke
from cli.renderables import render_intro, RenderSplits
from cli.utils import (
    grepo_md_theme,
    get_env_vars,
    check_models_api_key,
    update_env_var_api_keys,
    get_or_create_settings,
)
from cli.threads import initiate_threads

import click


@click.command()
def _main():
    # Clear screen
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.flush()

    # Get root dir of the codebase
    root_dir = os.getcwd()

    # Get API keys of LLMs from env variables
    env_vars = get_env_vars()

    # Create .grepo dir at root
    os.makedirs(f"{root_dir}/.grepo", exist_ok=True)

    # Read settings file
    settings_json = get_or_create_settings(root_dir)

    # --- Intial screen setup ---
    console = Console(highlight=False, theme=grepo_md_theme)

    # Welcome screen and (add intial model/api-key settings via arrow keys and toggle -> TODO)
    render_intro(console)

    # Run pre-processing to get information like programming languages used in codebase etc.
    preprocessed_data = preprocess_dir(root_dir)

    # Chat session uuid
    session_uuid = generate_session_uuid()

    # Thread initials
    lock = threading.Lock()
    query_queue = SimpleQueue()
    stop_event = threading.Event()
    output_queue = deque()
    buffer = ""

    # Create split regions for query processing and input bar
    split_screens = RenderSplits(output_queue=output_queue, lock=lock, console=console)

    thread_kwargs = {
        "query_queue": query_queue,
        "output_queue": output_queue,
        "lock": lock,
        "stop_event": stop_event,
    }

    # Initiate background processing threads
    input_processing_thread, logs_processing_thread = initiate_threads(
        root_dir,
        buffer,
        console,
        split_screens,
        session_uuid,
        preprocessed_data,
        **thread_kwargs,
    )

    live_region = Live(
        split_screens,
        refresh_per_second=60,
        console=console,
        transient=False,
    )

    try:
        live_region.start()

        # Check current env vars or grepo settings.json for API keys
        available_model_keys = check_models_api_key(env_vars, settings_json, root_dir)

        # If no API keys were found in env vars or settings.json then we ask user to select and input
        if not available_model_keys:
            # Show model selection and entering API keys screens
            with GetchRaw():
                Commands(console=console, rendered_regions=split_screens).show(
                    render_region="lower", screen_type="init"
                )
                split_screens.update_lower_split(main=True)

                # Update the env vars and settings.json for future sessions
                update_env_var_api_keys(Commands._api_keys, settings_json, root_dir)

        else:
            # Update the env vars and settings.json for future sessions
            update_env_var_api_keys(available_model_keys, settings_json, root_dir)

            # Render normal CLI if keys were found
            split_screens.update_lower_split(main=True)

        # Start background threads
        input_processing_thread.start()
        logs_processing_thread.start()

        while True:
            with GetchRaw():
                try:
                    while True:
                        char = read_keystroke()

                        if not char:
                            continue

                        # Toggle `thinking` mode if available
                        elif char == "\t":
                            query_queue.put(char)
                            continue

                        # Handle paste event (both regular multi-char and bracketed paste)
                        elif len(char) > 1 and not char.startswith("\x1b"):
                            buffer += char
                            split_screens.update_lower_split(buffer=buffer)
                            break

                        elif char.startswith("\x1b"):
                            continue

                        # --- Process user's query on `Enter` keystroke ---
                        elif char == "\n" and len(buffer) > 0 and buffer[-1] != "\n":
                            query_queue.put(f"> {buffer}")
                            break

                        elif char == "\x7f":  # `Backspace` keystroke
                            buffer = buffer[:-1]

                        # --- TODO: Improve how buffer addition is handled and edge cases better (works for now but improve ---
                        # Handle repeated `Enter` keystrokes
                        elif not buffer and char == "\n":
                            continue

                        # --- Add each character after all checks to the buffer and then update renderable ---
                        else:
                            buffer += char

                        # Just update the respective rendearble sections Rich picks up the diff and updates renderables
                        # Also we are already auto-refreshing the live region so we dont need to explicitly to call live.update()
                        split_screens.update_lower_split(buffer=buffer)

                        # Show commands palette and switch live region flow
                        if char == "/" and len(buffer) == 1:
                            split_screens._commands_palette_active = True
                            split_screens.update_footer_split(list_all_commands=True)
                            selected_command = Commands(
                                console=console, rendered_regions=split_screens
                            ).show(render_region="footer")

                            if len(selected_command) > 1:
                                buffer += selected_command
                            else:
                                # No command selected
                                buffer = buffer[:-1]

                            split_screens.update_lower_split(buffer=buffer)
                            split_screens.update_footer_split(blank=True)
                            split_screens._commands_palette_active = False

                # Ctrl-C keystroke
                except KeyboardInterrupt:
                    split_screens.update_footer_split(exit_screen=True)
                    split_screens.update_lower_split(buffer="")
                    stop_event.set()
                    break

            # Reset and clear buffer on `Enter` keystroke i.e submission of query
            buffer = ""
            split_screens.update_lower_split(console, buffer, is_first_time=False)

    except KeyboardInterrupt:
        pass

    finally:
        live_region.stop()
