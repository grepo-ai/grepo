# import os
# import glob
# import re
# from typing import Annotated, List, Tuple
# from typing_extensions import TypedDict

# from langchain_anthropic import ChatAnthropic
# from langgraph.graph import StateGraph, START, END
# from langgraph.graph.message import add_messages
# from langchain_core.tools import tool
# from langgraph.prebuilt import ToolNode, tools_condition
# from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage

# # from IPython.display import Image, display
# from dotenv import load_dotenv


# load_dotenv()

# # Define model to use
# anthropic_model = ChatAnthropic(
#     model="claude-sonnet-4-20250514",
#     max_tokens=64000,
#     thinking={"type": "enabled", "budget_tokens": 2000},
# )


# class AgentState(TypedDict):
#     messages: Annotated[list, add_messages]


# # Create tools for agent to use
# @tool
# def get_dir_path() -> str:
#     "Returns the absolute current directory path"
#     return os.getcwd()


# @tool
# def list_files(dir_path: str) -> List[str]:
#     "Takes a directory path and recursively lists all the files present with this directory as root"

#     file_paths = glob.glob(f"{dir_path}/**/*.py", recursive=True)
#     return file_paths


# @tool
# def read_file(file_path: str, query: str) -> str:
#     "Takes a file path and reads the contents of the file and returns the line that matches the content else returns `Not Found`"

#     with open(file_path, "r") as file:
#         file_contents = file.read().splitlines()

#     for line in file_contents:
#         if line == query:
#             return line
#         else:
#             return "Not Found"


# @tool
# def grep(query: str) -> Tuple[int, str, str]:
#     "This function performs a search on each file in current directory and return the line number and line where the query match is found else returns None"

#     file_paths = glob.glob(f"{os.getcwd()}/**/*.py", recursive=True)

#     query_matches = []
#     for path in file_paths:
#         with open(path, "r") as file:
#             for line_number, line in enumerate(file, 1):
#                 result = re.search(query, line)
#                 if result:
#                     query_matches.append((line_number, os.path.basename(path), line))

#     return query_matches


# tools = [get_dir_path, list_files, read_file, grep]

# # Bind the tools to model for it to use
# model_with_tools = anthropic_model.bind_tools(tools, parallel_tool_calls=False)


# # Define Nodes
# def assistant(state: AgentState):
#     tool_description = """

#         get_dir_path()
#             "Returns the absolute current directory path"

#             Returns:
#                 "Current directory path"

#         list_files(dir_path: str) -> List[str]:
#             "Takes a directory path and recursively lists all the files present with this directory as root"

#             Returns:
#                 List of file paths

#         read_file(file_path: str, query: str) -> str:
#             "Takes a file path and reads the contents of the file and returns the line that matches the content else returns `Not Found`"

#             Returns:
#                 Gives the line that matches the input query else returns "Not Found" if no match found in the file contents

#         grep(query: str) -> Tuple[int, str]:
#             "This function performs a global search on each file in current directory and return the line number,file path and line where the query match is found else returns None"

#     """

#     sys_msg = SystemMessage(
#         content=f"""You task is to find all the relevant lines that matches with the original query and return those lines.
#         If no matches are find then maybe it might be because of escape sequences or characters so fix those as well. \n Make use of the following tools to prepare a final answer. :{tool_description}\n""",
#         additional_kwargs={"cache_control": {"type": "ephemeral"}},
#     )

#     return {"messages": [model_with_tools.invoke([sys_msg] + state["messages"])]}


# if __name__ == "__main__":
#     from rich.console import Console
#     from rich.tree import Tree

#     # Rich formatting
#     console = Console()
#     tree = Tree("[#FF66FA]🔘 Search[/]")

#     # Build graph
#     graph_builder = StateGraph(AgentState)

#     # Add node
#     graph_builder.add_node("assistant", assistant)
#     graph_builder.add_node("tools", ToolNode(tools))

#     # Add edges
#     graph_builder.add_edge(START, "assistant")
#     graph_builder.add_conditional_edges("assistant", tools_condition)
#     graph_builder.add_edge("tools", "assistant")

#     agent = graph_builder.compile()

#     # print(display(Image(compiled_graph.get_graph(xray=True).draw_mermaid_png())))

#     # Test run
#     user_input = console.input("[#69FFB4]> [/]")
#     messages = [HumanMessage(content=user_input)]

#     for chunk in agent.stream(
#         config={"recursion_limit": 50},
#         input={"messages": messages},
#         stream_mode="updates",
#     ):
#         # console.print(chunk)
#         # console.print("------------")
#         # AI message
#         if chunk.get("assistant"):
#             message = chunk["assistant"]["messages"][0]
#             if isinstance(message, AIMessage):
#                 message = chunk["assistant"]["messages"][0].content
#                 if isinstance(message, list) and len(message) > 1:
#                     if message[1].get("text") is not None:
#                         console.print(
#                             f"[#CFCFCF]{chunk['assistant']['messages'][0].content[1]['text']}[/]"
#                         )
#                     else:
#                         console.print(
#                             f"[#CFCFCF]{chunk['assistant']['messages'][0].content[0]['text']}[/]"
#                         )

#                 else:
#                     message = chunk["assistant"]["messages"][0].content
#                     console.print(f"[#CFCFCF]{message}[/]")

#         # Print tool message
#         elif chunk.get("tools"):
#             tool_message = chunk["tools"]["messages"][0].content

#             if tool_message != "null":
#                 tree.add(f"[#FFDE7A]{tool_message}[/]")
#             elif tool_message == "null":
#                 tree.add("[#FFDE7A]Not Found[/]")
#             console.print(tree)
