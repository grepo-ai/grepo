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


if __name__ == "__main__":
    file_path = "/Users/tausif/grepo-main-env/grepo/src/agent/test1.py"
    old_code = """

    def merge_sort(arr: List[Any]) -> List[Any]:
        \"\"\"
        Sort a list using the merge sort algorithm.

        Args:
            arr: List to be sorted

        Returns:
            A new sorted list containing all elements from the input list

        Time Complexity: O(n log n)
        Space Complexity: O(n) for the recursive calls and temporary arrays
        \"\"\"
        if len(arr) <= 1:
            return arr.copy()  # Return a copy to maintain immutability

        mid = len(arr) // 2
        left_half = arr[:mid]
        right_half = arr[mid:]

        left_sorted = merge_sort(left_half)
        right_sorted = merge_sort(right_half)

        return merge(left_sorted, right_sorted)
    """
    new_code = ""

    diffs, patches = generate_diff(old_code, new_code, file_path)
    res = apply_diff(file_path, old_code, new_code)
    print(diffs)
    print("#########")
    print(res)
