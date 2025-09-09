import os
import glob
import re
from typing import Annotated, Optional, Union
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from src.agent.state import GlobalState
from langgraph.types import Command, interrupt


LIST_FILE_TOOL_DESCRIPTION = """

Takes a directory path and a boolean argument recursive as inputs.
- If the directory path is provided and recursive flag argument is passed as False then only files in the directory are returned.
- If directory path is provided and recursive argument is True then it recursively lists all the files present with this directory as root.
"""


# TODO: Also add a check to read .gitignore file and store the local absolute path of .gitignore file in graph state and
# read the file to find ignored files and avoid adding them to final to be returned list of file paths
@tool(description=LIST_FILE_TOOL_DESCRIPTION)
def list_files(
    dir_path: str,
    recursive: bool,
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Union[Command, list[str]]:
    path_exists = os.path.exists(dir_path)

    if not path_exists:
        return Command(
            update={
                "messages": [
                    ToolMessage("Path does not exist.", tool_call_id=tool_call_id)
                ]
            }
        )

    if recursive:
        file_paths = glob.glob(f"{dir_path}/**", recursive=True)
    else:
        file_paths = glob.glob(f"{dir_path}/*")

    if file_paths:
        return file_paths

    raise ValueError("No matches found for the path.")
