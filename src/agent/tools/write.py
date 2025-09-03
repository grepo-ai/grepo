import os
import glob as std_glob
import re
import tempfile
import shutil
from typing import Annotated, Optional, Union
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from src.agent.state import GlobalState
from langgraph.types import Command, interrupt
from agent.utils import apply_diff, generate_diff


WRITE_TOOL_DESCRIPTION = """

    Use this tool to create a new file to write the new data to the file or simply append new data to an existing file.

    ## IMPORTANT
     - code paramter should be used to pass the new generated code.
     - file_path is an optional parameter only use it if an existing file needs to me modified and new data has to be appended.
     - line_number parameter should be passed with the line number where the new generated code has to be included in the file.
     - If a new file is created which does not exists then line_number will always be 0.
     - New file names should be generated based on the semantic meaning of the newly generated code.
"""


@tool(description=WRITE_TOOL_DESCRIPTION)
def write(file_path: Optional[str], code: str, line_number: int = 0) -> str:
    # Check if file path exists else create new file with this name
    path_exists = os.path.exists(file_path)

    if not path_exists:
        with open(file_path, "w") as file:
            file.write(code)
    else:
        # If new content has to be added to an existing file with content
        # we first read old file and when we reach the line number where we need to add the code
        # block we append it. (File operation in this tool is same as in edit file tool)

        code_lines = code.splitlines()
        with (
            open(file_path, "r") as src_file,
            tempfile.NamedTemporaryFile(
                "w", delete=False, dir=os.path.dirname(file_path), encoding="utf-8"
            ) as tmp_file,
        ):
            tmp_name = tmp_file.name

            for line_no, line in enumerate(src_file, start=1):
                if line_no == line_number:
                    for code_line in code_lines:
                        tmp_file.write(code_line)

                tmp_file.write(line)

        shutil.copystat(file_path, tmp_name, follow_symlinks=False)
        os.replace(tmp_name, file_path)

    return f"code written to {file_path} successfully"
