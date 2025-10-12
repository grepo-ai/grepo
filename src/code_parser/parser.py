from enum import Enum
from collections import defaultdict
from typing import Optional
import os


from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_python as tspython
import tree_sitter_javascript as tsjavascript


from src.code_parser.queries import CODE_SYMBOLS_QUERY_MAP


language_map = {"py": "PYTHON", "js": "JAVASCRIPT", "ts": "TYPESCRIPT"}


class ParserLanguages(Enum):
    PYTHON = "py"
    JAVASCRIPT = "js"
    TYPESCRIPT = "ts"


class CodeWalker:
    def __init__(self, language: str):
        self._language_str = language
        self.language = self._set_language(language)
        self.parser = self._init_parser()
        self.queries = None  # TODO think of a better class design
        self.tree = None

    def _set_language(self, language):
        if language == ParserLanguages.PYTHON.value:
            set_language = Language(tspython.language())

        elif language == ParserLanguages.JAVASCRIPT.value:
            set_language = Language(tsjavascript.language())

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
            encoded_code=code,
            single_query=CODE_SYMBOLS_QUERY_MAP[self._language_str]["class"],
        )
        if parsed_code.get("class_name"):
            for class_name_node in parsed_code["class_name"]:
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

        if self._language_str in [
            ParserLanguages.JAVASCRIPT.value,
            ParserLanguages.TYPESCRIPT.value,
        ]:
            method_query = CODE_SYMBOLS_QUERY_MAP[self._language_str]["method"]
            parsed_code = self.parse(
                node=class_node,
                single_query=method_query,
            )
            if parsed_code.get("method_name"):
                for method_name_node in parsed_code["method_name"]:
                    class_methods.append(
                        {
                            "method_name": method_name_node.text.decode(),
                            "method_code": method_name_node.parent.text.decode(),
                            "file_path": file_path,
                        }
                    )

        elif self._language_str == ParserLanguages.PYTHON.value:
            method_query = CODE_SYMBOLS_QUERY_MAP[self._language_str]["function"]
            parsed_code = self.parse(
                node=class_node,
                single_query=method_query,
            )

            if parsed_code.get("function_name"):
                for method_name_node in parsed_code["function_name"]:
                    class_methods.append(
                        {
                            "method_name": method_name_node.text.decode(),
                            "method_code": method_name_node.parent.text.decode(),
                            "file_path": file_path,
                        }
                    )

        return class_methods

    def _extract_functions(self, code_map, code, file_path):
        # Tree node of the code parsed
        tree = self.parse(encoded_code=code)

        functions_list = []

        cursor = tree.root_node.walk()
        visited_children = False

        while True:
            if not visited_children:
                node = cursor.node

                if node.type in [
                    "function_definition",
                    "function_declaration",
                ] and node.parent.type in ["module", "program"]:
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
            single_query=CODE_SYMBOLS_QUERY_MAP[self._language_str]["function"],
        )

        for function_name_node in parsed_code["function_name"]:
            functions_map.append(
                {
                    "function_name": function_name_node.text.decode(),
                    "function_code": function_name_node.parent.text.decode(),
                    "file_path": file_path,
                }
            )

        code_map.update({"functions": functions_map})

        return code_map


# --- Test code ---
if __name__ == "__main__":
    from pathlib import Path
    import json

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

    import time, random

    # while True:
    #     user_input = input("enter a function block: ")
    #     print("##############")
    #     print(symbols_map)
    #     time.sleep(5)
