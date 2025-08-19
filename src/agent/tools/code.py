import os
import glob
import re
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState

from src.agent.state import GlobalState


CODE_BLOCK_TOOL_DESCRIPTION = """

    This tool is useful if you need to extract a code block definition by its name from the file or entire codebase.
    Tool input requires a file path for single file search or a recursive flag either True or False whether to search entire codebase,
    code block name could be a Class, Function, Method name this tool makes it easy to fetch a code block definition.

    ## When to use this tool:
    1. If a code block definition is required which could be a class, function or method.
    2. File path should be absolute not relative.
    3. If recursive flag is passed as True then it parses the entire codebase and fetches the code blocks matching the name.
    4. Code block name is a string and it can be a Class, Function or Method name.
    5. Tool returns a list of tuples where each tuple consists of a file path, code block name and code definition.

    ## Remember these points:
    1. When file path is passed then recursive should be passed False value.
    2. When recursive is passed as True then file path should be left empty.

"""


@tool(description=CODE_BLOCK_TOOL_DESCRIPTION)
def code_block(
    file_path: Optional[str], code_block_name: str, recursive: bool
) -> list[tuple[str, str, str]]:
    pass
