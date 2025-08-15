import os
import glob
import re
import uuid
from typing import Annotated, Union
from typing_extensions import TypedDict

from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.graph.state import CompiledStateGraph
from langgraph.graph.message import add_messages
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command, interrupt
from operator import add
import sqlite3


from dotenv import load_dotenv
from agent.tools import list_files, read_file, grep, edit_file
from agent.state import GlobalState
from agent.utils import get_checkpointer, generate_session_uuid
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

    # --- Text formatting ---
    console = Console()
    tree = Tree("[#FF66FA]> Search[/]")

    # --- Initialise LLM client ---
    llm_client = LLMInterface(llm_provider="anthropic")

    system_prompt = llm_client.get_system_prompt(
        prompt="""You are an experienced software engineer and your job is to help by answering code related questions,
    explain code and generate optimised and bug free and linted code to help answer the user's query also ensure code follows language specific best practices.
    Make the best use of the tools available at your disposal namely list files tool, read file tool, grep tool and edit file tool to apply the code change."""
    )

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
        tools=[list_files, read_file, grep, edit_file],
        schema=GlobalState,
        checkpointer=get_checkpointer(),
        system_prompt=system_prompt,
        config=agent_config,
        stream_mode="updates",
    )

    while True:
        user_input = console.input("[#69FFB4]> [/]")
        messages = [HumanMessage(content=user_input)]

        # ------ Invoke Agent ------
        running_agent = agent.stream(
            input={"messages": messages},
        )

        for chunk in running_agent:
            if chunk.get("agent"):
                ai_message = chunk["agent"]["messages"][0].content

                if isinstance(ai_message, list) and len(ai_message) > 1:
                    if ai_message[1].get("text") is not None:
                        console.print(
                            f"[#CFCFCF]{chunk['agent']['messages'][0].content[1]['text']}[/]"
                        )
                else:
                    console.print(
                        f"[#CFCFCF]{chunk['agent']['messages'][0].content}[/]"
                    )

            elif chunk.get("tools"):
                tool_message = chunk["tools"]["messages"][0].content
                tree.add(tool_message)

        print("------- Graph stopped for human approval ----")
        print(agent._compiled_graph.get_state(agent_config))

        human_approval = input("Enter Yes/No to accept/reject:")
        print("----- Resuming where graph stopped execution ----")

        running_agent = agent.stream(
            input=Command(resume={"option": human_approval}),
        )

        for chunk in running_agent:
            if chunk.get("agent"):
                ai_message = chunk["agent"]["messages"][0].content

                if isinstance(ai_message, list) and len(ai_message) > 1:
                    if ai_message[1].get("text") is not None:
                        console.print(
                            f"[#CFCFCF]{chunk['agent']['messages'][0].content[1]['text']}[/]"
                        )
                else:
                    console.print(
                        f"[#CFCFCF]{chunk['agent']['messages'][0].content}[/]"
                    )

            elif chunk.get("tools"):
                tool_message = chunk["tools"]["messages"][0].content
                tree.add(tool_message)
