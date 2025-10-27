import sys
import termios
import select
import tty
import time


class GetchRaw:
    """
    Context manager for reading raw terminal input.

    Note: When pasting text in iTerm2, the terminal buffers input and may not
    flush immediately. Users may need to press any key after pasting to trigger
    the display update. This is a known limitation of iTerm2's input handling
    in raw mode.
    """

    def __init__(self):
        self.fd = sys.stdin.fileno()

    def __enter__(self):
        self.old = termios.tcgetattr(self.fd)
        tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)


def read_keystroke():
    """
    Read a single keystroke or escape sequence from stdin.
    Returns None if no input available within timeout.
    """
    rlist, _, _ = select.select([sys.stdin], [], [], 0.02)
    if not rlist:
        return None

    ch = sys.stdin.read(1)

    # Handle escape sequences (arrow keys, etc.)
    if ch == "\x1b":
        return _read_escape_sequence()

    # Regular character
    return ch


def _read_escape_sequence():
    """Read and return a complete escape sequence"""
    seq = "\x1b"
    timeout = time.monotonic() + 0.05

    while time.monotonic() < timeout:
        rlist, _, _ = select.select([sys.stdin], [], [], 0.01)

        # if not rlist:
        #     break

        ch = sys.stdin.read(1)
        if not ch:
            break

        seq += ch

        # Arrow keys: \x1b[A (up), \x1b[B (down), \x1b[C (right), \x1b[D (left)
        if seq in ("\x1b[A", "\x1b[B"):
            break

        elif seq in ("\x1b[C", "\x1b[D"):
            seq = ""
            break

        # Other escape sequences - stop at reasonable length
        if len(seq) >= 6:
            break

    return seq
