"This file has sample code to test Tree-sitter and learn how it works"

from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from pprint import pprint

code = """
"test comment"
"test comment 2"
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

stmt_str_pattern = """(class_definition

   name: (identifier) @class_name
   body: (
   	(block
    	(function_definition) @class_methods
   ))

) @classes"""


stmt_str_query = py_language.query(stmt_str_pattern)

tree_captures = stmt_str_query.captures(tree.root_node)
pprint(tree_captures)

