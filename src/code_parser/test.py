"This file has sample code to test Tree-sitter and learn how it works"

import tree_sitter_python as tspython
from tree_sitter import Language, Parser

from code_parser import CodeWalker, ParserLanguages

code = """
class Thronefall:
    def __init__(self):
        self.level = 0
        self.player = 1
        self.army = {}

    def setup_player(self):
        return

    def play_game(self):
        return
"""


# Parse code
py_language = Language(tspython.language())
parser = Parser(py_language)
tree = parser.parse(code.encode())

test_query = """(class_definition

   name: (identifier) @class_name
   body: (
   	(block
    	(function_definition) @class_methods
   ))

) @classes"""


# stmt_str_query = py_language.query(test_query)

# tree_captures = stmt_str_query.captures(tree.root_node)


# --- Test code ---
if __name__ == "__main__":
    import json
    from pathlib import Path

    abs_file_path = "/Users/tausif/grepo-main-env/grepo/src/hello.js"
    file_path = str(Path(abs_file_path))

    # Create a parser
    code_walker = CodeWalker(ParserLanguages.JAVASCRIPT.value)

    # Pass in the code to be parsed
    encoded_code = CodeWalker.encode_code(file_paths=[abs_file_path])["hello.js"]

    # Construct code map with extracted code blocks (classes, functions and methods)
    symbols_map = code_walker.extract_symbols(encoded_code, file_path)

    print(json.dumps(symbols_map, indent=2))

    from rich.console import Console
    from rich.tree import Tree

    value = 0
    console = Console()
    tree = Tree("[#E8B641]Search[/]")
