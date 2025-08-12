import os
import glob
import re
from typing import Annotated, List, Tuple
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from cli.agent.agents2 import GlobalState
from langgraph.types import Command, interrupt


@tool
def list_files(dir_path: str) -> List[str]:
    "Takes a directory path and recursively lists all the files present with this directory as root"

    file_paths = glob.glob(f"{dir_path}/**/*.py", recursive=True)
    return file_paths


@tool
def read_file(file_path: str, query: str) -> str:
    "Takes a file path and reads the contents of the file and returns the line that matches the content else returns `Not Found`"

    with open(file_path, "r") as file:
        file_contents = file.read().splitlines()

    for line in file_contents:
        if line == query:
            return os.path.basename(file_path), line
        else:
            return os.path.basename(file_path), "Not Found"


@tool
def grep(query: str) -> Tuple[int, str, str]:
    "This function performs a recursive search on dirs/sub-dirs from root directory and returns all matches found for the given query else returns None"

    file_paths = glob.glob(f"{os.getcwd()}/**/*.py", recursive=True)

    query_matches = []
    for path in file_paths:
        with open(path, "r") as file:
            for line_number, line in enumerate(file, 1):
                result = re.search(query, line)
                if result:
                    query_matches.append((line_number, os.path.basename(path), line))

    return query_matches


@tool
def edit_file(
    generated_code: str,
    file_path: str,
    state: Annotated[GlobalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    """This tool is used to apply the generated code to a particular file only after approval from user else we dont change the file contents"""

    human_approval = interrupt({"generated_code": generated_code})
    code_diff = None

    if human_approval["option"].lower() in ("yes", "y"):
        with open(file_path, "r+") as file:
            pass

            # TODO: Find the diff in the file and apply the patch

        update_data = {
            "changed_code": code_diff,
            "messages": [
                ToolMessage(
                    f"Edited the file successfully and the generated code was accepted {file_path}",
                    tool_call_id=tool_call_id,
                )
            ],
        }

        return Command(update=update_data)

    elif human_approval["option"].lower() in ("no", "n"):
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"File not changed/edited the generated code was rejected {file_path}",
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )


# @tool
# def code_search():
#     """
#     This tool is useful to get the information about all the classes, methods or functions defined and used across the entire codebase.
#     It provides information like file path, name, start and end line numbers, references of the code symbol across the entire codebase.
#     """

#     pass


# @tool
# def get_code_block():
#     "For any class,method or function name fetch the entire code block"
