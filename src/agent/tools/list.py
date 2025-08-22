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


LIST_FILE_TOOL_DESCRIPTION = """

Takes a directory path and a boolean argument recursive as inputs.
- If the directory path is provided and recursive flag argument is passed as False then only files in the directory are returned.
- If directory path is provided and recursive argument is True then it recursively lists all the files present with this directory as root.
"""


@tool(description=LIST_FILE_TOOL_DESCRIPTION)
def list_files(dir_path: str, recursive: bool) -> list[str]:
    if recursive:
        file_paths = glob.glob(f"{dir_path}/**/*.py", recursive=True)
    else:
        file_paths = glob.glob(f"{dir_path}/*.py")
    return file_paths
