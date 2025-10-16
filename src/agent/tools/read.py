import os
import glob
import re
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from src.agent.state import GlobalState
from langgraph.types import Command, interrupt
from agent.utils import apply_diff, generate_diff


@tool
def read_file(file_path: str) -> list[Optional[str]]:
    "Takes a file path and reads the contents of the file and returns the contents for further use"

    file_contents = []
    try:
        # TODO: Add check for reading special files like pyproject.toml upto certain lines only
        # same for other language ecosystem files.
        with open(file_path, "r") as file:
            for line in file:
                file_contents.append(line)

        return file_path, file_contents
    except FileNotFoundError:
        raise ValueError("Not a valid file_path please provide a valid file path.")
