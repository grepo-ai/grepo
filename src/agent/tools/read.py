from langchain_core.tools import tool


@tool
def read_file(file_path: str) -> tuple[str, list[str]]:
    "Takes a file path and reads the contents of the file and returns the contents for further use"

    file_contents = []
    try:
        # TODO: Add check for reading special files like pyproject.toml upto certain lines only
        # same for other language ecosystem files.
        with open(file_path, "r") as file:
            for line in file:
                file_contents.append(line)

        return file_path, file_contents
    except FileNotFoundError:
        raise ValueError("Not a valid file_path please provide a valid file path.")
