import sys
import termios
import select
import tty
import time


# Set initial terminal state as context manager before reading input from stdin
class GetchRaw:
    def __init__(self):
        self.fd = sys.stdin.fileno()

    def __enter__(self):
        self.old = termios.tcgetattr(self.fd)
        self.tty_mode = tty.setcbreak(self.fd)
        return self

    def __exit__(self, exc_type, exc, tb):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)


# Read keystrokes from user
def read_keystroke():
    # tty.setraw(fd) # WOW read why this loc infinite glitched the live refresh panel everytime i keystroked

    rlist, _, _ = select.select([sys.stdin], [], [], 0.02)

    if not rlist:
        return None

    # Read first byte
    ch = sys.stdin.read(1)

    # Return non-sequence keystrokes i.e single char
    if ch != "\x1b":
        return ch

    # So we handled normal keystrokes now we know it is possibly an arrow sequence
    # (arrow keys are sequence of multiple bytes)
    # so we need to record that sequence (multi-byte) over a time range to make it look like single
    # logical key i.e arrow key (up/down/left/right)

    arrow_key_seq = ch

    seq_time_range = time.monotonic() + 0.05
    while time.monotonic() < seq_time_range:
        rlist, _, _ = select.select([sys.stdin], [], [], 0.01)

        next_char = sys.stdin.read(1)

        if not next_char:
            break

        arrow_key_seq += next_char

        # Check if complete sequence has been formed for UP and DOWN arrow keys
        if arrow_key_seq in ("\x1b[B", "\x1b[A"):
            break

        elif arrow_key_seq in ("\x1b[C", "\x1b[D"):
            continue

        # Hard check for any combination arrow sequence
        if len(arrow_key_seq) == 6:
            break

    return arrow_key_seq
