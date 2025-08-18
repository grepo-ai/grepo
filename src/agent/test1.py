"""
Merge sort implementation module.

This module contains an efficient implementation of the merge sort algorithm
with comprehensive documentation and type hints.
"""

from typing import List, Any


def merge(left: List[Any], right: List[Any]) -> List[Any]:
    """
    Merge two sorted lists into a single sorted list.

    Args:
        left: First sorted list
        right: Second sorted list

    Returns:
        A new sorted list containing all elements from both input lists

    Time Complexity: O(n + m) where n and m are lengths of input lists
    Space Complexity: O(n + m) for the result list
    """
    result = []
    l_index = 0
    r_index = 0

    # Merge elements while both lists have remaining items
    while l_index < len(left) and r_index < len(right):
        if left[l_index] <= right[r_index]:
            result.append(left[l_index])
            l_index += 1
        else:
            result.append(right[r_index])
            r_index += 1

    # Add remaining elements from left list
    while l_index < len(left):
        result.append(left[l_index])
        l_index += 1

    # Add remaining elements from right list
    while r_index < len(right):
        result.append(right[r_index])
        r_index += 1

    return result


def merge_sort(arr: List[Any]) -> List[Any]:
    """
    Sort a list using the merge sort algorithm.

    Args:
        arr: List to be sorted

    Returns:
        A new sorted list containing all elements from the input list

    Time Complexity: O(n log n)
    Space Complexity: O(n) for the recursive calls and temporary arrays
    """
    if len(arr) <= 1:
        return arr.copy()  # Return a copy to maintain immutability

    mid = len(arr) // 2
    left_half = arr[:mid]
    right_half = arr[mid:]

    left_sorted = merge_sort(left_half)
    right_sorted = merge_sort(right_half)


# Test functions
def test_merge_empty_lists():
    """Test merging two empty lists."""
    assert merge([], []) == []


def test_merge_one_empty_list():
    """Test merging when one list is empty."""
    assert merge([], [1, 2, 3]) == [1, 2, 3]
    assert merge([1, 2, 3], []) == [1, 2, 3]


def test_merge_sorted_lists():
    """Test merging two sorted lists."""
    assert merge([1, 3, 5], [2, 4, 6]) == [1, 2, 3, 4, 5, 6]
    assert merge([1, 2, 3], [4, 5, 6]) == [1, 2, 3, 4, 5, 6]
    assert merge([4, 5, 6], [1, 2, 3]) == [1, 2, 3, 4, 5, 6]


def test_merge_with_duplicates():
    """Test merging lists with duplicate elements."""
    assert merge([1, 3, 3], [2, 3, 4]) == [1, 2, 3, 3, 3, 4]


def test_merge_single_elements():
    """Test merging single element lists."""
    assert merge([1], [2]) == [1, 2]
    assert merge([2], [1]) == [1, 2]


def test_merge_sort_empty_list():
    """Test sorting an empty list."""
    assert merge_sort([]) == []


def test_merge_sort_single_element():
    """Test sorting a single element list."""
    assert merge_sort([5]) == [5]


def test_merge_sort_sorted_list():
    """Test sorting an already sorted list."""
    assert merge_sort([1, 2, 3, 4, 5]) == [1, 2, 3, 4, 5]


def test_merge_sort_reverse_sorted():
    """Test sorting a reverse sorted list."""
    assert merge_sort([5, 4, 3, 2, 1]) == [1, 2, 3, 4, 5]


def test_merge_sort_random_list():
    """Test sorting a randomly ordered list."""
    assert merge_sort([3, 1, 4, 1, 5, 9, 2, 6]) == [1, 1, 2, 3, 4, 5, 6, 9]


def test_merge_sort_with_duplicates():
    """Test sorting a list with duplicate elements."""
    assert merge_sort([3, 3, 1, 1, 2, 2]) == [1, 1, 2, 2, 3, 3]


def test_merge_sort_negative_numbers():
    """Test sorting a list with negative numbers."""
    assert merge_sort([-3, -1, -4, -1, -5]) == [-5, -4, -3, -1, -1]


def test_merge_sort_mixed_numbers():
    """Test sorting a list with mixed positive and negative numbers."""
    assert merge_sort([-1, 3, -4, 2, 0]) == [-4, -1, 0, 2, 3]


def test_merge_sort_strings():
    """Test sorting a list of strings."""
    assert merge_sort(["banana", "apple", "cherry"]) == ["apple", "banana", "cherry"]


def test_merge_sort_immutability():
    """Test that the original list is not modified."""
    original = [3, 1, 4, 1, 5]
    sorted_copy = merge_sort(original)
    assert original == [3, 1, 4, 1, 5]  # Original should be unchanged
    assert sorted_copy == [1, 1, 3, 4, 5]


if __name__ == "__main__":
    # Run basic tests when script is executed directly
    print("Running basic tests...")

    # Test merge function
    test_merge_empty_lists()
    test_merge_one_empty_list()
    test_merge_sorted_lists()
    test_merge_with_duplicates()
    test_merge_single_elements()

    # Test merge_sort function
    test_merge_sort_empty_list()
    test_merge_sort_single_element()
    test_merge_sort_sorted_list()
    test_merge_sort_reverse_sorted()
    test_merge_sort_random_list()
    test_merge_sort_with_duplicates()
    test_merge_sort_negative_numbers()
    test_merge_sort_mixed_numbers()
    test_merge_sort_strings()
    test_merge_sort_immutability()

    print("All tests passed!")
