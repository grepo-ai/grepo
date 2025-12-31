import os
from typing import Annotated, Optional

from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState

from agent.state import GlobalState
from code_parser import CodeWalker, ParserLanguages, language_map

CODE_BLOCK_TOOL_DESCRIPTION = """

    This tool is useful if you need to extract a code block definition by its name from the file.
    Tool input requires a file path for search.
    code block name could be a Class, Function, Method name this tool makes it easy to fetch a code block definition.

    ## When to use this tool:
    1. If a code block definition is required which could be a class, function or method.
    2. File path should be absolute not relative.
    3. Code block name is a string and it can be a Class, Function or Method name.
    4. Tool returns a list of tuples where each tuple consists of a file path, code block name and code definition.

    ## Important:
    1. This tool will fail if no code block name or file path is provided.
    2. file path should be a valid code file with an extension.
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
        file_extension = os.path.splitext(file_path)[1]

        if not file_extension:
            raise ValueError("file_path is not a code file")

        source_code_lang = language_map.get(file_extension.strip("."))
        if not source_code_lang:
            raise ValueError("Not a valid code file with this extension")

        code_walker = CodeWalker(getattr(ParserLanguages, f"{source_code_lang}").value)

        encoded_code = CodeWalker.encode_code(file_paths=[file_path])[
            os.path.basename(file_path)
        ]

        # Construct code map with extracted code blocks (classes, functions and methods)
        symbols_map = code_walker.extract_symbols(encoded_code, file_path)

        for klass in symbols_map.get("classes", []):
            if klass["class_name"] == code_block_name:
                return klass["class_code"]

            for method in klass.get("class_methods", []):
                if method["method_name"] == code_block_name:
                    return method["method_code"]

        for function in symbols_map.get("functions", []):
            if function["function_name"] == code_block_name:
                return function["function_code"]

        raise ValueError("No code definition found in this file.")

    raise ValueError("Provide a valid file_path argument")


# Idea: Multi-threaded tree cursor based traversal of each file.
