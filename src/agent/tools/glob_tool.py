import os
import glob as std_glob
import re
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from src.agent.state import GlobalState
from langgraph.types import Command, interrupt
from agent.utils import apply_diff, generate_diff

GLOB_TOOL_DESCRIPTION = """

This tool is useful when you need to find a file path by a specific pattern.

## IMPORTANT
  - Pattern can be an absolute file path like /usr/src/hello.py (finds this particular file in /usr/src directory) or
    it could be a relative pattern like /usr/src/*.py (finds all .py files in /usr/src directory)
  - If a pattern has ** in it then it has to be searched recursively for example
    /usr/**/*.py this will search for all directories, sub-directories and find all .py files.
"""


# TODO: Think more on possible edge cases and add examples in tool description
@tool(description=GLOB_TOOL_DESCRIPTION)
def glob(pattern: str) -> list[str]:
    recursive = True if "**" in pattern else False
    file_paths = std_glob.iglob(pattern, recursive=recursive)

    return file_paths
