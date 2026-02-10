import os
import shutil
import tempfile

from langchain_core.tools import tool

WRITE_TOOL_DESCRIPTION = """
    Use this tool to create a new file to write the new data to the file or simply append new data in an existing file.

    ## IMPORTANT
     - Do not use this tool to make edits to existing content in file.
     - code paramter should be used to pass the new generated code.
     - pathname is an optional parameter only use it if an existing file needs to me modified and new data has to be appended.
     - line_number parameter should be passed with the line number where the new generated code has to be included in the file.
     - If a new file is created which does not exists then line_number will always be 0.
     - New file names should be generated based on the semantic meaning of the newly generated code.
     - If the pathname is just a directory then do not pass any code or line_number parameter.
     - Always make sure if pathname is a directory then end the pathname with a `/'
"""


@tool(description=WRITE_TOOL_DESCRIPTION)
def write(pathname: str, code: str, line_number: int = 0) -> str:
    try:
        # Check if pathname exists else create required directories and files based on type
        path_exists = os.path.exists(pathname)

        if not path_exists:
            head, tail = os.path.split(pathname)

            # If one level less from pathname the path doesnt exist then we create a dir first
            if not os.path.exists(head):
                os.makedirs(head)

            # Then we check if tail is a dir or file path
            is_dir = True if pathname.endswith(os.sep) or "." not in tail else False

            # is_file = (
            #     True
            #     if "." in os.path.basename(pathname)
            #     and not os.path.basename(pathname).startswith(".")
            #     else False
            # )

            if is_dir:
                os.makedirs(pathname, exist_ok=True)
                return f"Directory with {pathname} created successfully"

            # Finally this is a file so we write the code to it
            with open(pathname, "w") as file:
                file.write(code)

        else:
            # If new content has to be added to an existing file with content
            # we first read old file and when we reach the line number where we need to add the code block
            # we append it from that point. (append operation in this tool is same as in edit file tool)

            code_lines = code.splitlines()
            with (
                open(pathname, "r") as src_file,
                tempfile.NamedTemporaryFile(
                    "w", delete=False, dir=os.path.dirname(pathname), encoding="utf-8"
                ) as tmp_file,
            ):
                tmp_name = tmp_file.name

                for line_no, line in enumerate(src_file, start=1):
                    if line_no == line_number:
                        for code_line in code_lines:
                            tmp_file.write(code_line)

                    tmp_file.write(line)

            shutil.copystat(pathname, tmp_name, follow_symlinks=False)
            os.replace(tmp_name, pathname)

        return f"code written to {pathname} successfully"

    except Exception as err:
        raise ValueError(str(err))
