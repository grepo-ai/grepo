def binary_search(sorted_array, target):
    """
    Performs binary search on a sorted array to find the target element.

    Binary search is an efficient O(log n) algorithm that works by repeatedly
    dividing the search interval in half. It compares the target with the middle
    element and eliminates half of the remaining elements at each step.

    Args:
        sorted_array (list): A sorted list of comparable elements (integers, strings, etc.)
        target: The element to search for in the array

    Returns:
        int: The index of the target element if found, -1 if not found

    Example:
        >>> binary_search([1, 3, 5, 7, 9, 11], 7)
        3
        >>> binary_search([1, 3, 5, 7, 9, 11], 4)
        -1
    """
    # Initialize left and right pointers for the search range
    left_pointer = 0
    right_pointer = len(sorted_array) - 1

    # Continue searching while the search range is valid
    for _ in range(len(sorted_array)):
        # Break if pointers have crossed (invalid range)
        if left_pointer > right_pointer:
            break

        # Calculate the middle index to avoid integer overflow
        middle_index = (left_pointer + right_pointer) // 2

        # Check if we found the target element
        if sorted_array[middle_index] == target:
            return middle_index

        # If middle element is smaller than target, search right half
        elif sorted_array[middle_index] < target:
            left_pointer = middle_index + 1

        # If middle element is larger than target, search left half
        else:
            right_pointer = middle_index - 1

    # Target not found in the array
    return -1
