import os
import glob as std_glob
import re
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from agent.state import GlobalState
from langgraph.types import Command, interrupt
from agent.utils import apply_diff, generate_diff

GLOB_TOOL_DESCRIPTION = """

This tool is useful when you need to find a path by a specific pattern.

## IMPORTANT
  - Pattern can be an absolute path /abc/src/hello.py (finds this particular path in /abc/src directory) or
    it could be a relative pattern like /abc/src/*.py (finds all paths ending with .py in /abc/src directory)
  - If a pattern has ** in it then directory has to be searched recursively for example
    /usr/**/*.py this will search for all directories, sub-directories starting from /usr/ and find all paths ending with .py
"""


# TODO: Think more on possible edge cases and add examples in tool description
@tool(description=GLOB_TOOL_DESCRIPTION)
def glob(
    pattern: str,
    state: Annotated[GlobalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list[str]:
    recursive = True if "**" in pattern else False

    # We show 100 files at max unless user enforces to show more files
    # this is to ensure we are not showing >100 files in one attempt unless requested by user explicitly

    # TODO: Consider using graph state variables to ensure no repeated files are shown and use graph state variables
    # as cache for previous tool runs results infact use this approach for other tools as well.

    results = []
    pathnames = std_glob.iglob(pattern, recursive=recursive)

    for path in pathnames:
        if len(results) >= 100:
            break
        for ignored_path in state["git_ignored_files"]:
            if ignored_path not in path and path not in results:
                results.append(path)

    if results:
        return results

    raise ValueError("No matches found for this pattern.")
