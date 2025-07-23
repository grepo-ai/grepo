# Different types of tree sitter queries to extract code symbols
CODE_SYMBOLS_QUERY_MAP = {
    "classes": """
    (class_definition

       name: (identifier) @class_names
    ) @classes

    """,
    "functions": """
    ( function_definition

	name: (identifier) @function_names
	body: (block) @function_blocks

     ) @functions


    """,
}
