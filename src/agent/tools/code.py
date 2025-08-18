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
