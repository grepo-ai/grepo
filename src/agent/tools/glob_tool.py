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

This tool is useful when you need to find a path by a specific pattern.

## IMPORTANT
  - Pattern can be an absolute path /usr/src/hello.py (finds this particular path in /usr/src directory) or
    it could be a relative pattern like /usr/src/*.py (finds all paths ending with .py in /usr/src directory)
  - If a pattern has ** in it then directory has to be searched recursively for example
    /usr/**/*.py this will search for all directories, sub-directories starting from /usr/ and find all paths ending with .py
"""


# TODO: Think more on possible edge cases and add examples in tool description
@tool(description=GLOB_TOOL_DESCRIPTION)
def glob(pattern: str) -> list[str]:
    recursive = True if "**" in pattern else False

    # We show 100 files at max unless user enforces to show more files
    # this is to ensure we are not showing >100 files in one attempt unless requested by user explicitly
    results = []
    pathnames = std_glob.iglob(pattern, recursive=recursive)

    for path in pathnames:
        if len(results) > 100:
            break
        results.append(path)

    if results:
        return results

    raise ValueError("No matches found for this pattern.")
