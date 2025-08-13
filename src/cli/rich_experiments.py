# === cool demo of making a spinner with built-in lib ===
# import itertools
# import sys
# from time import sleep

# spinner = itertools.cycle(["-", "/", "|", "\\"])
# busy = True
# while busy:
#     sys.stdout.write(next(spinner))  # write the next character
#     sys.stdout.flush()  # flush stdout buffer (actual character display)
#     sys.stdout.write("\b")  # erase the last written char
#     sleep(1)


### === Menu toggle demo === ###
# from rich.live import Live
# from rich.console import Console
# from rich.panel import Panel
# import time

# console = Console()


# def make_panel(counter):
#     return Panel(f"Counter: {counter}", title="Live Demo")


# live = Live(make_panel(0), console=console, refresh_per_second=10)
# live.start()  # begin live rendering

# try:
#     for i in range(6):
#         live.update(make_panel(i))
#         time.sleep(0.4)

#         if i == 2:
#             # pause the live region, print outside it, then resume
#             live.stop()
#             console.print("[bold yellow]Live paused — doing external output[/]")
#             console.print("Some important message that appears outside the panel.")
#             time.sleep(1)  # simulate work
#             live.start()  # resume live rendering

#     live.update(make_panel("done"))
#     time.sleep(0.5)
# finally:
#     live.stop()  # ensure it's fully stopped
#     console.print("[green]Live has been stopped permanently.[/]")


# import sys
# import termios
# import tty
# from contextlib import contextmanager
# from rich.panel import Panel
# from rich.live import Live
# from rich.console import Console

# console = Console()

# _BACKSPACE_CHARS = {"\x7f", "\b", "\x08"}


# @contextmanager
# def _unix_raw_mode(file):
#     fd = file.fileno()
#     old_attrs = termios.tcgetattr(fd)
#     try:
#         tty.setcbreak(fd)
#         yield
#     finally:
#         termios.tcsetattr(fd, termios.TCSADRAIN, old_attrs)


# def read_char() -> str:
#     if sys.platform == "win32":
#         import msvcrt

#         ch = msvcrt.getwch()
#         return "\n" if ch == "\r" else ch
#     else:
#         with _unix_raw_mode(sys.stdin):
#             ch = sys.stdin.read(1)
#         return ch


# def read_key() -> str:
#     """
#     Normalizes raw input into logical keys: UP, DOWN, SPACE, ENTER, ESC, single chars, etc.
#     """
#     ch = read_char()
#     # Handle escape sequences on Unix (arrow keys)
#     if ch == "\x1b":
#         # try to read the rest of the sequence (usually 2 more chars)
#         if sys.platform != "win32":
#             rest = sys.stdin.read(2)
#             seq = ch + rest
#             if seq == "\x1b[A":
#                 return "UP"
#             if seq == "\x1b[B":
#                 return "DOWN"
#             if seq == "\x1b[C":
#                 return "RIGHT"
#             if seq == "\x1b[D":
#                 return "LEFT"
#         return "ESC"
#     if sys.platform == "win32":
#         # On Windows, arrow keys come as prefix '\x00' or '\xe0' then code
#         if ch in ("\x00", "\xe0"):
#             import msvcrt

#             code = msvcrt.getwch()
#             if code == "H":
#                 return "UP"
#             if code == "P":
#                 return "DOWN"
#             if code == "M":
#                 return "RIGHT"
#             if code == "K":
#                 return "LEFT"
#             return "UNKNOWN"
#     if ch == "\n":
#         return "ENTER"
#     if ch == " ":
#         return "SPACE"
#     if ch in ("\x03",):  # Ctrl-C
#         return "CTRL_C"
#     if ch in ("\x1b",):
#         return "ESC"
#     return ch  # fallback: literal character


# def interactive_toggle(options: list[str]) -> list[str]:
#     """
#     Let user toggle multiple options interactively. Returns list of selected options.
#     """
#     selected = [False] * len(options)
#     idx = 0  # current cursor position

#     def make_panel():
#         lines = []
#         for i, opt in enumerate(options):
#             pointer = ">" if i == idx else " "
#             mark = "[bold green]✔[/]" if selected[i] else " "
#             lines.append(f"{pointer} [{mark}] {opt}")
#         lines.append("")  # spacing
#         lines.append(
#             "↑/↓: move  space: toggle  a: all  n: none  Enter: confirm  q/Esc: cancel"
#         )
#         return Panel(
#             "\n".join(lines),
#             title="Select Options",
#             border_style="magenta",
#             padding=(1, 2),
#         )

#     with Live(
#         make_panel(), refresh_per_second=10, console=console, transient=False
#     ) as live:
#         while True:
#             key = read_key()
#             if key == "UP":
#                 idx = (idx - 1) % len(options)
#             elif key == "DOWN":
#                 idx = (idx + 1) % len(options)
#             elif key == "SPACE":
#                 selected[idx] = not selected[idx]
#             elif key.lower() == "a":
#                 for i in range(len(selected)):
#                     selected[i] = True
#             elif key.lower() == "n":
#                 for i in range(len(selected)):
#                     selected[i] = False
#             elif key == "ENTER":
#                 break
#             elif key in ("q", "ESC"):
#                 selected = [False] * len(options)
#                 break
#             elif key == "CTRL_C":
#                 raise KeyboardInterrupt
#             live.update(make_panel())

#     console.print()  # newline to separate
#     return [opt for opt, sel in zip(options, selected) if sel]


# def main():
#     opts = ["Option A", "Option B", "Option C", "Option D"]
#     picked = interactive_toggle(opts)
#     if picked:
#         console.print(f"Selected: {', '.join(picked)}")
#     else:
#         console.print("[yellow]No selection made or cancelled.[/]")


# if __name__ == "__main__":
#     main()


# import sys
# import time
# import threading
# import select
# import termios
# import tty
# from collections import deque
# from queue import SimpleQueue

# from rich.console import Console
# from rich.live import Live
# from rich.panel import Panel
# from rich.text import Text
# from rich.spinner import Spinner
# from rich.align import Align

# console = Console()


# # Context manager to set raw mode once
# class RawMode:
#     def __init__(self, fd):
#         self.fd = fd

#     def __enter__(self):
#         self.old = termios.tcgetattr(self.fd)
#         tty.setraw(self.fd)
#         return self

#     def __exit__(self, exc_type, exc, tb):
#         termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)


# # Read one key or full escape sequence (arrow keys, etc.)
# _ESC_SEQ_RE = __import__("re").compile(r"^\x1b\[?[0-9;?]*[A-Za-z~]$")


# def read_key(fd, initial_timeout=0.02, seq_timeout=0.05):
#     rlist, _, _ = select.select([fd], [], [], initial_timeout)
#     if not rlist:
#         return None
#     ch = sys.stdin.read(1)
#     if ch != "\x1b":
#         return ch
#     # possible escape sequence: accumulate
#     seq = ch
#     deadline = time.monotonic() + seq_timeout
#     while time.monotonic() < deadline:
#         rlist, _, _ = select.select([fd], [], [], 0)
#         if not rlist:
#             time.sleep(0.001)
#             continue
#         more = sys.stdin.read(1)
#         if not more:
#             break
#         seq += more
#         if _ESC_SEQ_RE.match(seq) or len(seq) > 6:
#             break
#     return seq


# def input_thread_func(cmd_queue, buffer_obj, stop_event, fd):
#     with RawMode(fd):
#         while not stop_event.is_set():
#             key = read_key(fd)
#             if key is None:
#                 continue
#             # handle special keys
#             if key in ("\r", "\n"):
#                 with buffer_obj["lock"]:
#                     cmd = buffer_obj["buf"]
#                     buffer_obj["buf"] = ""
#                 if cmd.strip():
#                     cmd_queue.put(cmd.strip())
#             elif key in ("\x7f", "\b"):  # backspace
#                 with buffer_obj["lock"]:
#                     buffer_obj["buf"] = buffer_obj["buf"][:-1]
#             elif key == "\x03":  # ctrl-c
#                 stop_event.set()
#                 break
#             else:
#                 # ignore escape sequences (like arrows) for typing
#                 if len(key) == 1 and ord(key) >= 32:
#                     with buffer_obj["lock"]:
#                         buffer_obj["buf"] += key
#             # small sleep to prevent busy spin
#             time.sleep(0.005)


# def make_panel(progress, log_lines, current_input):
#     # build log area (show last few)
#     log_text = Text()
#     for line in log_lines:
#         log_text.append(line + "\n")
#     # build input prompt
#     prompt = Text.assemble(
#         ("[You]> ", "bold cyan"),
#         (current_input, "white"),
#         ("_", "bold yellow"),  # cursor indicator
#     )
#     # combine
#     body = Text()
#     body.append(f"Progress: {progress}\n")
#     body.append(log_text)
#     body.append("\n")
#     body.append(prompt)
#     panel = Panel(
#         Align.left(body),
#         title="Processing & Interactive Input",
#         border_style="bright_blue",
#         padding=(1, 2),
#     )
#     return panel


# def main():
#     fd = sys.stdin.fileno()
#     cmd_queue = SimpleQueue()
#     buffer_obj = {"buf": "", "lock": threading.Lock()}
#     stop_event = threading.Event()
#     log = deque(maxlen=50)
#     progress = 0

#     input_thread = threading.Thread(
#         target=input_thread_func,
#         args=(cmd_queue, buffer_obj, stop_event, fd),
#         daemon=True,
#     )
#     input_thread.start()

#     spinner = Spinner("dots", text="Working...", style="#ff8800")

#     with Live(console=console, refresh_per_second=100, screen=False) as live:
#         while not stop_event.is_set():
#             # Simulate progress
#             progress += 1
#             if progress > 100:
#                 progress = 100
#             spinner.text = f"[bold]Step {progress}/100[/]"
#             # Check for entered commands
#             while not cmd_queue.empty():
#                 cmd = cmd_queue.get()
#                 log.append(f"[{time.strftime('%H:%M:%S')}] Command received: {cmd}")
#                 # Example: if user types 'exit' stop
#                 if cmd.lower() in ("q", "quit", "exit"):
#                     log.append("Exit command, shutting down.")
#                     stop_event.set()
#             # Read current input buffer
#             with buffer_obj["lock"]:
#                 current_input = buffer_obj["buf"]
#             # Prepare combined panel
#             panel = make_panel(f"{progress}%", list(log)[-10:], current_input)
#             # Combine spinner and panel side by side
#             container = Panel(
#                 Align.left(panel),
#                 subtitle="Type something and press Enter. Type 'exit' to quit.",
#                 border_style="green",
#             )
#             live.update(container)
#             if progress >= 100:
#                 log.append("Processing finished.")
#                 # keep running to accept commands, or break if desired
#             time.sleep(0.1)

#     console.print("\n[bold green]Shutting down. Final log:[/]")
#     for line in log:
#         console.print(line)


# if __name__ == "__main__":
#     try:
#         main()
#     except KeyboardInterrupt:
#         console.print("\n[red]Interrupted by user[/]")


import sys
import termios
import tty
import select
import time
from rich.live import Live
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.text import Text
from rich import box
from contextlib import contextmanager

console = Console()


@contextmanager
def raw_mode(file):
    old_attrs = termios.tcgetattr(file.fileno())
    try:
        tty.setcbreak(file.fileno())
        yield
    finally:
        termios.tcsetattr(file.fileno(), termios.TCSADRAIN, old_attrs)


def read_key(timeout=0.1):
    dr, _, _ = select.select([sys.stdin], [], [], timeout)
    if not dr:
        return None
    ch1 = sys.stdin.read(1)
    if ch1 == "\x1b":
        # try to consume a common escape sequence (e.g., arrow keys) but we don't need those here
        dr2, _, _ = select.select([sys.stdin], [], [], 0.01)
        if dr2:
            ch2 = sys.stdin.read(1)
            dr3, _, _ = select.select([sys.stdin], [], [], 0.01)
            if dr3:
                ch3 = sys.stdin.read(1)
                return f"\x1b[{ch3}"
            return ch1 + ch2
    return ch1


def make_input_panel(label, content, active, width=60, cursor_on=False):
    label = label or ""
    content = content or ""
    display = content
    if active and cursor_on:
        display += "_"
    elif active:
        display += " "  # keep width consistent when cursor blink off

    txt = Text.assemble((f"{label}: ", "bold"), (display, "white"))
    border_style = "bright_green" if active else "dim"
    return Panel(
        txt,
        border_style=border_style,
        padding=(0, 1),
        width=width,
        title=label if active else "",
        subtitle="(active)" if active else "",
        box=box.ROUNDED,  # compact box instead of None
    )


def build_layout(states, active_idx, cursor_on):
    root = Layout()
    root.split_column(
        Layout(name="input1", size=3),
        Layout(name="input2", size=3),
        # Layout(name="summary", ratio=1),
    )

    panel1 = make_input_panel(
        states[0]["label"],
        states[0]["value"],
        active_idx == 0,
        width=60,
        cursor_on=cursor_on,
    )
    panel2 = make_input_panel(
        states[1]["label"],
        states[1]["value"],
        active_idx == 1,
        width=60,
        cursor_on=cursor_on,
    )

    # summary_text = Text()
    # summary_text.append("Current values:\n", style="bold underline")
    # summary_text.append(f"{states[0]['label']}: {states[0]['value']}\n")
    # summary_text.append(f"{states[1]['label']}: {states[1]['value']}\n\n")
    # summary_text.append(
    #     "[Tab] switch  [Backspace] delete  [Enter] submit  [Esc] exit", style="dim"
    # )
    # summary_panel = Panel(
    #     summary_text,
    #     border_style="blue",
    #     title="Summary",
    #     padding=(1, 1),
    #     width=60,
    #     box=box.SIMPLE,
    # )

    root["input1"].update(panel1)
    root["input2"].update(panel2)
    # root["summary"].update(summary_panel)
    return root


def main():
    states = [{"label": "First", "value": ""}, {"label": "Second", "value": ""}]
    active = 0
    cursor_blink_interval = 0.5
    last_blink = time.time()
    cursor_on = True

    console.clear()
    with raw_mode(sys.stdin):
        with Live(
            build_layout(states, active, cursor_on),
            console=console,
            refresh_per_second=10,
        ) as live:
            while True:
                now = time.time()
                if now - last_blink >= cursor_blink_interval:
                    cursor_on = not cursor_on
                    last_blink = now
                    live.update(build_layout(states, active, cursor_on))

                key = read_key(timeout=0.05)
                if key is None:
                    continue

                if key == "\x1b":  # ESC
                    break
                if key in ("\r", "\n"):  # Enter
                    break
                if key == "\t":  # Tab
                    active = (active + 1) % len(states)
                    live.update(build_layout(states, active, cursor_on))
                    continue
                if key in ("\x7f", "\b"):  # Backspace
                    if states[active]["value"]:
                        states[active]["value"] = states[active]["value"][:-1]
                        live.update(build_layout(states, active, cursor_on))
                    continue
                if len(key) == 1 and 32 <= ord(key) <= 126:
                    states[active]["value"] += key
                    live.update(build_layout(states, active, cursor_on))
                    continue

    console.print("\nFinal input:")
    console.print(f"{states[0]['label']}: [bold]{states[0]['value']}[/bold]")
    console.print(f"{states[1]['label']}: [bold]{states[1]['value']}[/bold]")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
