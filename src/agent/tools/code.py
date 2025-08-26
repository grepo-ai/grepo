import os
import glob
import re
import json
from typing import Annotated, Optional
from typing_extensions import TypedDict

from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.messages import ToolMessage
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, interrupt


from src.agent.state import GlobalState
from src.code_parser import CodeWalker, ParserLanguages


CODE_BLOCK_TOOL_DESCRIPTION = """

    This tool is useful if you need to extract a code block definition by its name from the file.
    Tool input requires a file path for single file search.
    code block name could be a Class, Function, Method name this tool makes it easy to fetch a code block definition.

    ## When to use this tool:
    1. If a code block definition is required which could be a class, function or method.
    2. File path should be absolute not relative.
    3. Code block name is a string and it can be a Class, Function or Method name.
    4. Tool returns a list of tuples where each tuple consists of a file path, code block name and code definition.

    ## Important:
    1. This tool will fail if no code block name is provided.
"""


@tool(description=CODE_BLOCK_TOOL_DESCRIPTION)
def get_code_block(
    file_path: Optional[str],
    code_block_name: str,
    # recursive: bool,
    state: Annotated[GlobalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> list[tuple[str, str, str]]:
    # Return with a message for tool failure
    if not code_block_name:
        raise ValueError("code_block_name cannot be empty")

    if file_path:
        # TODO: Infer language from graph state variables
        code_walker = CodeWalker(ParserLanguages.PYTHON.value)

        encoded_code = CodeWalker.encode_code(file_paths=[file_path])[
            os.path.basename(file_path)
        ]

        # Construct code map with extracted code blocks (classes, functions and methods)
        symbols_map = code_walker.extract_symbols(encoded_code, file_path)

        for klass in symbols_map["classes"]:
            if klass["class_name"] == code_block_name:
                return klass["class_code"]

            for method in klass["class_methods"]:
                if method["method_name"] == code_block_name:
                    return method["method_code"]

        for function in symbols_map["functions"]:
            if function["function_name"] == code_block_name:
                return function["function_code"]

        raise ValueError("code definition not found in this file.")


# TODO: Maybe consider doing grep from this code tool as well for code block search across codebase
# Idea: Multi-threaded tree cursor based traversal of each file.
