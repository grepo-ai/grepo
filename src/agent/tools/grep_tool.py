import os
import re
from typing import Annotated

from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState

from agent.state import GlobalState


@tool
def grep(
    pattern: str,
    state: Annotated[GlobalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list[tuple[str, int, str]]:
    """
    This function performs a recursive search on all directories/sub-directories from root directory and returns all matches found for the given pattern, tool
    returns file_path, line number and matched line for each match of the pattern else it returns empty list if no match is found
    """

    pattern_matches = []
    for root, dirs, files in os.walk(state["root_dir"]):
        if (
            "." in root or root in state["git_ignored_files"]
        ):  # skip .dir names eg: .venv and if dir is in .gitignore
            continue

        for file_name in files:
            if file_name in state["git_ignored_files"]:
                continue

            file_extension = os.path.splitext(file_name)[1]
            if file_extension and file_extension.strip(".") in state["languages"]:
                with open(os.path.join(root, file_name), "r") as file:
                    for line_number, line in enumerate(file, 1):
                        result = re.search(pattern, line)
                        if result:
                            pattern_matches.append(
                                (os.path.join(root, file_name), line_number, line)
                            )

    if pattern_matches:
        return pattern_matches

    raise ValueError("No matches found for the pattern.")
