from tree_sitter import Language, Parser
import tree_sitter_python as tspython
from enum import Enum
from typing import List
import os


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

    def parse(self, encoded_code: str, single_query: str):
        # Parses the code and gets the `root` node
        self.tree = self.parser.parse(encoded_code)

        # If `single_query` provided it takes precedence over multiple queries
        if single_query:
            tree_sitter_query = self.language.query(single_query)
            node_captures = tree_sitter_query.captures(self.tree.root_node)

            return node_captures

        else:
            # TODO handle multiple queries if needed to maybe?
            pass

        return

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
