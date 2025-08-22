import os
import glob
import re
import uuid
import json
from typing import Annotated, Union
from typing_extensions import TypedDict


from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command, interrupt
from operator import add
import sqlite3


from dotenv import load_dotenv
from agent.tools import list_files, read_file, grep, edit_file, get_code_block
from agent.state import GlobalState
from agent.utils import (
    get_checkpointer,
    generate_session_uuid,
    construct_code,
    format_grep_results,
)
from agent.llm import LLMInterface


load_dotenv()


class Agent:
    def __init__(
        self,
        model,
        tools: list,
        schema,
        checkpointer,
        system_prompt: str,
        stream_mode: Union[str, list],
        config: dict = {},
    ):  # TODO: complete type hints for class
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools
        self.state_schema = schema
        self.stream_mode = stream_mode
        self.checkpointer = checkpointer
        self._config = config
        self._compiled_graph: CompiledStateGraph = None

    @property
    def config(self):
        return self._config

    @property
    def agent_state(self):
        return self._compiled_graph

    def _create(self):
        self._compiled_graph = create_react_agent(
            self.model,
            tools=self.tools,
            state_schema=self.state_schema,
            checkpointer=self.checkpointer,
            prompt=self.system_prompt,
        )

        return self._compiled_graph

    def stream(self, input):
        # Create and agent with provided config
        live_agent = self._create()

        # Returns a new generator on each new invocation of user input
        # else simply use the generator object to get stream updates
        return live_agent.stream(
            input=input, config=self._config, stream_mode=self.stream_mode
        )


# --------------------------------------------------- #


# --------------------------------------------------------- #
# ------(TODO: temp) Agents will be called from CLI ------- #
# --------------------------------------------------------- #


if __name__ == "__main__":
    from rich.console import Console
    from rich.tree import Tree
    from pathlib import Path
    from rich.markdown import Markdown

    # --- Text formatting ---

    console = Console()
    tree_grep = Tree("[#E8B641]> ✱ Search[/]")

    tree_list = Tree("[#E8B641]> ✱ List[/]")
    tree_read = Tree("[#E8B641]> ✱ Read[/]")

    # --- Initialise LLM client ---
    llm_client = LLMInterface(llm_provider="anthropic")

    # --- Read GREPO.md for system prompt and instructions ---
    model_prompt = Path(f"{os.getcwd()}/GREPO.md").read_text(encoding="utf-8")

    system_prompt = llm_client.get_system_prompt(prompt=model_prompt)

    # --- Check if user need to resume old session or start new ---
    session_uuid = console.input("Enter a session uuid to resume conversation: ")
    if not session_uuid:
        session_uuid = generate_session_uuid()

    agent_config = {
        "configurable": {"thread_id": session_uuid},
        "recursion_limit": 50,
    }

    # --- Create an Agent ---
    agent = Agent(
        model=llm_client.client(),
        tools=[list_files, read_file, grep, edit_file, get_code_block],
        schema=GlobalState,
        checkpointer=get_checkpointer(),
        system_prompt=system_prompt,
        config=agent_config,
        stream_mode="updates",
    )
    # Add graph state variables :
    # 1. preference for edit files
    # 2. files or dirs to be ignored
    # 3. language of the repo
    while True:
        user_input = console.input("[#69FFB4]> [/]")
        messages = [HumanMessage(content=user_input)]

        # --- This inner while loop ensures we have ended one complete cycle of agent inovcation ---
        input_type = {"messages": messages}
        agent_cycle_active = True
        while True:
            running_agent = agent.stream(
                input=input_type,
            )

            for stream_message in running_agent:
                # print(stream_message)
                # print("\n\n")
                # Stream chunk type 1: Agent response
                if stream_message.get("agent"):
                    ai_messages = stream_message["agent"]["messages"][0].content

                    if isinstance(ai_messages, list):
                        for msg in ai_messages:
                            if msg.get("thinking"):
                                console.print(
                                    f"[#60FCF5]Thinking: {msg['thinking']}[/]\n"
                                )

                            elif msg.get("text"):
                                console.print(f"[#CFCFCF]{msg['text']}[/]")
                    else:
                        markdown_text = Markdown(ai_messages)
                        console.print(markdown_text)

                # Stream chunk type 2: Tool response
                elif stream_message.get("tools"):
                    # Check type of tool and populate tree alerts accordingly
                    tool_name = stream_message["tools"]["messages"][0].name
                    tool_message = stream_message["tools"]["messages"][0].content

                    # List files
                    if tool_name == "list_files":
                        tree_list.add("[#FA5CB3]Analysing files and directories...[/]")

                        console.print(tree_list)

                    # Read file
                    elif tool_name == "read_file":
                        if tool_message is None:
                            continue
                        read_file_data = json.loads(tool_message)
                        code_snippet, file_path = construct_code(
                            read_file_data, truncate=True
                        )

                        tree_read.add(f"[#FA5CB3]Reading ({file_path})[/]")

                        console.print(tree_read)
                        # console.print(
                        #     f"[#7CFCA7]{code_snippet} \n ------------------- \n [/] [#E8B641]File location: {file_path}[/]",
                        #     highlight=False,
                        # )

                    # Grep file(s)
                    elif tool_name == "grep":
                        # No results found by `grep` tool
                        if not tool_message:
                            continue

                        grep_content_list = json.loads(tool_message)
                        formatted_grep_results = format_grep_results(grep_content_list)

                        sub_tree_grep = Tree(
                            f"[#FA5CB3]Matches found ({len(formatted_grep_results)})[/]"
                        )
                        tree_grep.add(sub_tree_grep)
                        for res in formatted_grep_results:
                            sub_tree_grep.add(f"{res[0]}--{res[1]}")

                        console.print(tree_grep)

                # Stream chunk type 3: Interrupt response
                elif stream_message.get("__interrupt__"):
                    old_code = stream_message["__interrupt__"][0].value["old_code"]
                    new_code = stream_message["__interrupt__"][0].value["new_code"]
                    console.print(old_code, highlight=False)
                    console.print("[#CFCFCF]----------Code Diff------------[/]")
                    console.print(new_code, highlight=False)

                    human_approval = console.input("Enter Yes/No to accept/reject:")

                    input_type = Command(resume={"option": human_approval})

                # Condition to check if agent loop has ended or continues with the current cycle
                graph_state_values = agent._compiled_graph.get_state(
                    agent_config
                ).values
                last_ai_response = -1
                for index, msg in enumerate(graph_state_values["messages"]):
                    if isinstance(msg, AIMessage):
                        last_ai_response = max(last_ai_response, index)

                if last_ai_response > 0:
                    llm_response_metadata = graph_state_values["messages"][
                        last_ai_response
                    ].response_metadata

                    stop_reason = llm_response_metadata["stop_reason"]

                    # Officially marks the end of Agent loop
                    if stop_reason == "end_turn":
                        agent_cycle_active = False
                        break

            if not agent_cycle_active:
                break
