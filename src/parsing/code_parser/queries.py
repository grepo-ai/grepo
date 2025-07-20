# Different types of tree sitter queries to extract code symbols
CODE_SYMBOLS_QUERY_MAP = {
    "classes": """
    (class_definition

       name: (identifier) @class_name
       body: (
       	(block
        	(function_definition) @class_methods
       ))

    ) @classes
    """,
    "functions": "",
}
