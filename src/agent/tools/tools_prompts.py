EDIT_TOOL_DESCRIPTION = """

    Edits a file by first opening it and reading its contents using the absolute file path provided as input parameter. Then applies the generated code as the new
    edit to the contents and saves it. Carefully consider the following usage guidelines for the appropriate use of this tool.

    ## Usage guidelines:
    - Pass the absolute file path in order to open it and make edits.
    - Structure of generated code should be in this format :
      <START>ONLY 1 line of code just BEFORE new generated code this code is unchanged and as in original file</START>
      <DIFF>actual generated code or modified code that is new addition or deletion</DIFF>
      <END>ONLY 1 line of code just AFTER new generated code this code is unchanged and as in original file</END>

    - <START>Tag is used to denote the last line just before actual new generated code is given for edit,
              Line of code inside this tag is same as original code and remains unchanged.
      <DIFF>This is the actual generated/deleted code diff produced which needs to be applied to the file.
      <END>This tag has the line of code just after the generated code that is same as in original file and remains unchanged.

    - <DIFF> diff block can be mulit-line code.
    - <START> and <END> should only be 1 line of code.
    - Generate well formatted code following proper code practices and conventions of the particular programming language.

    ## Examples of how the input to this tool should look like:
        <example>

        <START>def func(a,b):</START> * one line befroe generated diff this line is unchanged as in original file *
        <DIFF>data_docs = load_data()</DIFF> * actual code diff generated that needs to be applied *
        <END>return ("=== Successfully embedded the documents ===")</END> * one line after the diff code block this line is unchanged as in original file *

        </example>

        <example>

        <START>if single_query and not node:</START>
        <DIFF>tree_sitter_query = self.language.query(single_query)</DIFF>
        <END>node_captures = tree_sitter_query.captures(self.tree.root_node)</END>

        </example>

        <example>
        <DIFF>
        def binary_search(sorted_array, target):
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
        </DIFF>
        </example>
"""
