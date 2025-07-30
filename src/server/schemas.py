from pydantic import BaseModel
from typing import List, Optional, Any


class CreateIndex(BaseModel):
    index_name: str
    override: bool
    embedding_size: int
    models_name: str  # alibaba_modernbert or answerdotai_modernbert


class IndexCode(BaseModel):
    code_blocks: List[str]
    ids: Optional[List[int]] = None
    models_name: str  # alibaba_modernbert or answerdotai_modernbert


class RetrievedResults(BaseModel):
    query: Any
    code_blocks: Any
    models_name: str  # alibaba_modernbert or answerdotai_modernbert


"""
class FenwickTree:
    def __init__(self, size):
        # Initialize the tree with 0s (1-indexed)
        self.n = size
        self.tree = [0] * (self.n + 1)

    def update(self, index, delta):
        \\\"""
        Adds 'delta' to the element at 'index'.
        Time Complexity: O(log n)
        \\\"""
        while index <= self.n:
            self.tree[index] += delta
            index += index & -index  # Move to parent index

    def query(self, index):
        \\\"""
        Returns the prefix sum from 1 to 'index'.
        Time Complexity: O(log n)
        \\\"""
        result = 0
        while index > 0:
            result += self.tree[index]
            index -= index & -index  # Move to ancestor index
        return result

    def range_query(self, left, right):
        \\\"""
        Returns the sum of elements in the range [left, right].
        Time Complexity: O(log n)
        \\\"""
        return self.query(right) - self.query(left - 1)
"""
