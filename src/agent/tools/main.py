import os
import glob
import re
from typing import Annotated
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from src.cli.agent.state import GlobalState
from langgraph.types import Command, interrupt
from agent.tools.tools_prompts import EDIT_TOOL_DESCRIPTION


@tool
def list_files(dir_path: str) -> list[str]:
    "Takes a directory path and recursively lists all the files present with this directory as root"

    file_paths = glob.glob(f"{dir_path}/**/*.py", recursive=True)
    return file_paths


@tool
def read_file(file_path: str) -> str:
    "Takes a file path and reads the contents of the file and returns the contents for further use"

    with open(file_path, "r") as file:
        file_contents = file.read()
        return file_contents


@tool
def grep(query: str) -> list[tuple[str, int, str]]:
    """
    This function performs a recursive search on all directories/sub-directories from root directory and returns all matches found for the given query along
    with file file_paths for each query match else returns empty list if no match is found
    """
    # Add code_search (DB search) tool logic into this tool to make it very precise and purposeful

    file_paths = glob.glob(f"{os.getcwd()}/**/*.py", recursive=True)

    query_matches = []
    for path in file_paths:
        with open(path, "r") as file:
            for line_number, line in enumerate(file, 1):
                result = re.search(query, line)
                if result:
                    query_matches.append((os.path.basename(path), line_number, line))

    return query_matches


@tool(description=EDIT_TOOL_DESCRIPTION)
def edit_file(
    generated_code: str,
    file_path: str,
    state: Annotated[GlobalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:
    print(" --- entering approval before making an edit ---")
    human_approval = interrupt({"generated_code": generated_code})
    code_diff = None

    if human_approval["option"].lower() in ("yes", "y"):
        print(file_path)
        print("--------")
        print(generated_code)

        with open(file_path, "r+") as file:
            file.write(generated_code)
        # TODO: Write edit logic complety

        update_data = {
            "changed_code": generated_code,
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
