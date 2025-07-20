from dotenv import load_dotenv
from pprint import pprint


load_dotenv()


if __name__ == "__main__":
    from src.code_parser import CodeWalker, ParserLanguages
    from src.code_parser.queries import CODE_SYMBOLS_QUERY_MAP

    parser = CodeWalker(ParserLanguages.PYTHON.value)

    # Pass in the code to be parsed
    code = CodeWalker.encode_code(
        file_path="/Users/tausif/grepo-main/grepo/src/benchmarks/dino_game.py"
    )["dino_game.py"]
    parsed_code = parser.parse(
        encoded_code=code, single_query=CODE_SYMBOLS_QUERY_MAP["classes"]
    )
