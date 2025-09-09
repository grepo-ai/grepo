# Different types of tree sitter queries to extract code symbols
CODE_SYMBOLS_QUERY_MAP = {
    "class": """
    (class_definition

       name: (identifier) @class_name
    ) @classes

    """,
    "function": """
    ( function_definition

	name: (identifier) @function_name
	body: (block) @function_block

     ) @functions


    """,
}
