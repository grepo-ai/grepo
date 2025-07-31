from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from enum import Enum
from collections import defaultdict
from typing import List
import os
from queries import CODE_SYMBOLS_QUERY_MAP


class ParserLanguages(Enum):
    PYTHON = "py"


class CodeWalker:
    def __init__(self, language: str):
        self.language = self._set_language(language)
        self.parser = self._init_parser()
        self.queries = None  # TODO think of a better class design
        self.tree = None

    def _set_language(self, language):
        if language == ParserLanguages.PYTHON.value:
            set_language = Language(tspython.language())

        return set_language

    def _init_parser(self):
        return Parser(self.language)

    @property
    def get_parser(self):
        return self.parser

    def parse(self, encoded_code: str = None, single_query: str = None, node=None):
        """Parses the code or captures the node for a given query pattern"""

        if encoded_code:
            self.tree = self.parser.parse(encoded_code)

        # If `single_query` provided it takes precedence over multiple queries
        if single_query and not node:
            tree_sitter_query = self.language.query(single_query)
            node_captures = tree_sitter_query.captures(self.tree.root_node)

            return node_captures

        elif single_query and node:
            tree_sitter_query = self.language.query(single_query)
            node_captures = tree_sitter_query.captures(node)

            return node_captures

        return self.tree

    @staticmethod
    def encode_code(
        file_path: str = None, dir_path: str = None, ignore_files: List[str] = []
    ):
        """
        Parses all the code files and ignores the list of files passed in `ignore_files`.
        This is also a recursive operation if `dir_path` is passed.
        """

        # Map has the structure where key: file name and value: encoded code
        encoded_code_map = {}
        if file_path:
            filename = os.path.basename(file_path)

            if filename not in ignore_files:
                with open(file_path, "r") as file:
                    contents = file.read()
                    encoded_contents = contents.encode("utf-8")

                    encoded_code_map[filename] = encoded_contents
            else:
                return None

        return encoded_code_map

    def extract_symbols(self, encoded_code, file_path):
        classes_symbols_map = self._extract_classes(encoded_code, file_path)
        complete_symbols_map = self._extract_functions(
            classes_symbols_map, encoded_code, file_path
        )

        return complete_symbols_map

    def _extract_classes(self, code, file_path):
        code_blocks = defaultdict(list)

        parsed_code = self.parse(
            encoded_code=code, single_query=CODE_SYMBOLS_QUERY_MAP["classes"]
        )
        for class_name_node in parsed_code["class_names"]:
            code_blocks["classes"].append(
                {
                    "class_name": class_name_node.text.decode(),
                    "class_code": class_name_node.parent.text.decode(),
                    "class_methods": self._extract_class_methods(
                        class_name_node.parent,
                        class_name_node.text.decode(),
                        file_path,
                    ),
                    "file_path": file_path,
                }
            )
        return code_blocks

    def _extract_class_methods(self, class_node, class_name, file_path):
        class_methods = []
        parsed_code = self.parse(
            node=class_node, single_query=CODE_SYMBOLS_QUERY_MAP["functions"]
        )
        for method_name_node in parsed_code["function_names"]:
            class_methods.append(
                {
                    "method_name": method_name_node.text.decode(),
                    "method_code": method_name_node.parent.text.decode(),
                    "file_path": file_path,
                }
            )

        return class_methods

    def _extract_functions(self, code_map, code, file_path):
        # Tree object of the code parsed
        tree = self.parse(encoded_code=code)

        functions_list = []

        cursor = tree.root_node.walk()
        visited_children = False

        while True:
            if not visited_children:
                node = cursor.node

                if node.type == "function_definition" and node.parent.type == "module":
                    functions_list.append(node.text.decode())
                if not cursor.goto_first_child():
                    visited_children = True

            elif cursor.goto_next_sibling():
                visited_children = False

            elif not cursor.goto_parent():
                break

        # Use queries to extract nested sub-functions inside functions
        functions_map = []

        parsed_code = self.parse(
            encoded_code="\n".join(functions_list).encode(),
            single_query=CODE_SYMBOLS_QUERY_MAP["functions"],
        )

        for function_name_node in parsed_code["function_names"]:
            functions_map.append(
                {
                    "function_name": function_name_node.text.decode(),
                    "function_code": function_name_node.parent.text.decode(),
                    "file_path": file_path,
                }
            )

        code_map.update({"functions": functions_map})

        return code_map


if __name__ == "__main__":
    from pathlib import Path
    import json

    abs_file_path = (
        "/Users/tausif/grepo-main-env/grepo/src/indexing/benchmarks/dino_game.py"
    )
    file_path = str(Path(abs_file_path))

    # Create a parser
    code_walker = CodeWalker(ParserLanguages.PYTHON.value)

    # Pass in the code to be parsed
    encoded_code = CodeWalker.encode_code(file_path=abs_file_path)["dino_game.py"]

    # Construct code map with extracted code blocks (classes, functions and methods)
    symbols_map = code_walker.extract_symbols(encoded_code, file_path)

    print(json.dumps(symbols_map, indent=2))
