from typing import Annotated, Optional

from langchain_core.messages import ToolMessage
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command, interrupt

from agent.state import GlobalState
from agent.utils import apply_diff, generate_diff

EDIT_TOOL_DESCRIPTION = """

    This tool is best used for making file edits for adding/removing/modifying existing text.

    ## CRITICAL REQUIREMENTS FOR USING THIS TOOL:
    - Use read_file tool first to read the contents of the file before using this tool.
    - Pass the absolute path of the file.
    - New code addition to file should be sent in new_code parameter.
    - The tool will replace ONE occurrence of old_string with new_string in the specified file by default.
    - Include all whitespace, indentation, and surrounding code exactly as it appears in the file
    - old_code MUST identify with an exact match in the file so provide 2/3 lines of context BEFORE and AFTER
      the new_code parameter value.

    ## UNIQUE CASES:
    - If code has to be removed/deleted send code to be removed in old_code parameter and keep new_code parameter EMPTY.
    - DO NOT SEND ANY VALUE TO new_code IF ANY CODE HAS TO BE REMOVED OR DELETED.

    ## WARNINGS:
    - Do not leave code in broken or half completed state, ensure code generated is bug free, concise and optimised.
    - Make sure old_code has exact strings as in file (including whitespaces) otherwise tool will fail

"""


@tool(description=EDIT_TOOL_DESCRIPTION)
def edit_file(
    old_code: Optional[str],
    new_code: Optional[str],
    file_path: str,
    state: Annotated[GlobalState, InjectedState],
    tool_call_id: Annotated[str, InjectedToolCallId],
) -> Command:  # ty:ignore[invalid-return-type]
    # Highlighted and formatted diff text
    old_highlight, new_highlight = generate_diff(
        old_code, new_code, file_path, highlight=True
    )

    human_approval = interrupt({"old_code": old_highlight, "new_code": new_highlight})

    if human_approval["option"].lower() in ("yes", "y"):
        # TODO: Improve edit functionality
        apply_diff(file_path, old_code, new_code)

        update_data = {
            "messages": [
                ToolMessage(
                    f"Edited the file successfully and the generated code was accepted {file_path}",
                    tool_call_id=tool_call_id,
                )
            ]
        }

        return Command(update=update_data)

    elif human_approval["option"].lower() in ("no", "n"):
        return Command(
            update={
                "messages": [
                    ToolMessage(
                        f"File not edited the generated code was rejected try again and reason well and provide right context. {file_path}",
                        tool_call_id=tool_call_id,
                    )
                ]
            }
        )
