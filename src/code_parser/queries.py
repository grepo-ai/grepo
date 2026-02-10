# Different types of tree sitter queries to extract code symbols
CODE_SYMBOLS_QUERY_MAP = {
    "py": {
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
    },
    "js": {
        "class": """

        (class_declaration

         	name: (identifier) @class_name
            body : (class_body ) @class_body
         ) @classes

        """,
        "method": """
            (method_definition
              name: (property_identifier) @method_name
              body: (statement_block) @method_body) @methods

            """,
        "function": """
            (function_declaration
              name: (identifier) @function_name
              body: (statement_block) @function_block)
            @functions
            """,
    },
    "ts": {},
}
