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

    - <DIFF> diff block can be mulit-line code that was generated.
    - <START> and <END> are only 1 line of code strictly.

    ## Examples of how the input to this tool should look like:
        <example>

        <START> def func(a,b):</START> * one line befroe generated diff this line is unchanged as in original file *
        <DIFF> data_docs = load_data()</DIFF> * actual code diff generated that needs to be applied *
        <END> print("=== Successfully embedded the documents ===")</END> * one line after the diff code block this line is unchanged as in original file *

        </example>

        <example>

        <START>if single_query and not node:</START>
        <DIFF>tree_sitter_query = self.language.query(single_query)</DIFF>
        <END>node_captures = tree_sitter_query.captures(self.tree.root_node)</END>

        </example>
"""
