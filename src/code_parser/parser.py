from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython
from enum import Enum
from collections import defaultdict
from typing import Optional
import os
from src.code_parser.queries import CODE_SYMBOLS_QUERY_MAP


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
    def _parser(self):
        return self.parser

    def create_query(self, query_expression: str, language: Language):
        query = Query(language, query_expression.encode("utf-8"))
        return query

    def create_query_cursor(self, query: Query) -> QueryCursor:
        query_cursor = QueryCursor(query)
        return query_cursor

    def parse(self, encoded_code: str = None, single_query: str = None, node=None):
        """Parses the code or captures the node for a given query pattern"""

        if encoded_code:
            self.tree = self.parser.parse(encoded_code)

        if single_query:
            tree_sitter_query = self.create_query(single_query, self.language)
            query_cursor = self.create_query_cursor(tree_sitter_query)

        # If `single_query` provided it takes precedence over multiple queries
        if single_query and not node:
            node_captures = query_cursor.captures(self.tree.root_node)
            return node_captures

        elif single_query and node:
            node_captures = query_cursor.captures(node)
            return node_captures

        return self.tree

    @staticmethod
    def encode_code(
        file_paths: Optional[list[str]] = None,
        dir_path: str = None,
        ignore_files: list[str] = [],
    ):
        """
        Parses all the code files and ignores the list of files passed in `ignore_files`.
        This is also a recursive operation if `dir_path` is passed.
        """

        # Map has the structure where key: file name and value: encoded code
        encoded_code_map = {}
        if file_paths:
            for file_path in file_paths:
                filename = os.path.basename(file_path)

                if filename not in ignore_files:
                    with open(file_path, "r") as file:
                        contents = file.read()
                        encoded_contents = contents.encode("utf-8")

                        encoded_code_map[filename] = encoded_contents
                else:
                    encoded_code_map[filename] = None

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
        if parsed_code.get("class_names"):
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

        if parsed_code.get("function_names"):
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

        # No function definitions found
        if not functions_list:
            return code_map

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

    abs_file_path = "/Users/tausif/grepo-main-env/grepo/src/code_parser/parser.py"
    file_path = str(Path(abs_file_path))

    # Create a parser
    code_walker = CodeWalker(ParserLanguages.PYTHON.value)

    # Pass in the code to be parsed
    encoded_code = CodeWalker.encode_code(file_paths=[abs_file_path])["parser.py"]

    # Construct code map with extracted code blocks (classes, functions and methods)
    symbols_map = code_walker.extract_symbols(encoded_code, file_path)

    # print(json.dumps(symbols_map, indent=2))

    from rich.console import Console
    from rich.tree import Tree

    value = 0
    console = Console()
    tree = Tree("[#E8B641]Search[/]")

    import time, random

    while True:
        sub_tree = Tree(f"[#F048D7]Matches found ({value})[/]")
        tree.add(sub_tree)
        sub_tree.add("hello")

        console.print(tree)
        value = random.randint(1, 10)
        time.sleep(3)
