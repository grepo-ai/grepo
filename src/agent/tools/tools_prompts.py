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
