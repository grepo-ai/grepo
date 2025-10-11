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
def grep(
    query: str,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list[tuple[str, int, str]]:
    """
    This function performs a recursive search on all directories/sub-directories from root directory and returns all matches found for the given query, tool
    returns file_path, line number and matched line for each match of the query else it returns empty list if no match is found
    """

    file_paths = glob.glob(f"{os.getcwd()}/**/*.py", recursive=True)

    query_matches = []
    for path in file_paths:
        with open(path, "r") as file:
            for line_number, line in enumerate(file, 1):
                result = re.search(query, line)
                if result:
                    query_matches.append((path, line_number, line))

    if query_matches is not None:
        return query_matches

    raise ValueError("No matches found for the query.")
