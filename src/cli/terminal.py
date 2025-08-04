import os
import sys
import termios
import select
import tty
import time
from rich.console import Console
from rich.align import Align
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.padding import Padding
from rich.box import HEAVY_EDGE, ROUNDED, DOUBLE_EDGE, HEAVY, Box
import pyfiglet


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
