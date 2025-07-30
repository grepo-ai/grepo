from dotenv import load_dotenv
from pprint import pprint
from collections import defaultdict
from pydantic import BaseModel
from typing import List
from pathlib import Path
import os

from code_parser import CodeWalker, ParserLanguages, CODE_SYMBOLS_QUERY_MAP


load_dotenv()


class ClassObjs(BaseModel):
    name: str
    body: str
    methods: List[str]
    file_path: str


def extract_classes(code, parser, file_path):
    code_blocks = defaultdict(list)

    parsed_code = parser.parse(
        encoded_code=code, single_query=CODE_SYMBOLS_QUERY_MAP["classes"]
    )
    for class_name_node in parsed_code["class_names"]:
        code_blocks["classes"].append(
            {
                "class_name": class_name_node.text.decode(),
                "class_code": class_name_node.parent.text.decode(),
                "class_methods": extract_class_methods(
                    class_name_node.parent,
                    class_name_node.text.decode(),
                    file_path,
                ),
                "file_path": file_path,
            }
        )
    return code_blocks


def extract_class_methods(class_node, class_name, file_path):
    class_methods = []
    parsed_code = parser.parse(
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


def extract_functions(code_map, code, parser, file_path):
    # Tree object of the code parsed
    tree = parser.parse(encoded_code=code)

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

    parsed_code = parser.parse(
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
    abs_file_path = (
        "/Users/tausif/grepo-main-env/grepo/src/parsing/benchmarks/dino_game.py"
    )
    file_path = str(Path(abs_file_path))

    # Create a parser
    parser = CodeWalker(ParserLanguages.PYTHON.value)

    # Pass in the code to be parsed
    code = CodeWalker.encode_code(file_path=abs_file_path)["dino_game.py"]

    # Construct code map with extracted code blocks (classes, functions and methods)
    code_blocks_map = extract_classes(code, parser, file_path)
    updated_code_blocks_map = extract_functions(
        code_map=code_blocks_map, code=code, parser=parser, file_path=file_path
    )

    import json

    print(json.dumps(updated_code_blocks_map, indent=2))
