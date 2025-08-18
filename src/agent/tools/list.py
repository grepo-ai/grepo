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
def list_files(dir_path: str) -> list[str]:
    "Takes a directory path and recursively lists all the files present with this directory as root"

    file_paths = glob.glob(f"{dir_path}/**/*.py", recursive=True)
    return file_paths
