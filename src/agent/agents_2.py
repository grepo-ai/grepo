import os
import glob
import re
import uuid
from typing import Annotated
from typing_extensions import TypedDict


from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
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

# Load env vars
load_dotenv()


# Declare a checkpoint
checkpointer = SqliteSaver(sqlite3.connect("grepo.db", check_same_thread=False))


# # ---- TODO: learn how to integrate prompt caching
anthropic_model = ChatAnthropic(
    model="claude-sonnet-4-20250514",
    max_tokens=64000,
    thinking={"type": "enabled", "budget_tokens": 2000},
)


# Create system prompt along with pormpt caching TODO: Learn more about best caching techniques to lower token burn
system_prompt = SystemMessage(
    content=[
        {
            "text": """You are an experienced software engineer and your job is to help by answering code related questions,
            explain code and generate optimised and bug free and linted code to help answer the user's query also ensure code follows language specific best practices.
            Make the best use of the tools available at your disposal namely list files tool, read file tool, grep tool and edit file tool to apply the code change.""",
            "type": "text",
            "cache_control": {"type": "ephemeral"},
        }
    ]
)

# Create a ReAct agent
agent = create_react_agent(
    anthropic_model,
    tools=[list_files, read_file, grep, edit_file],
    state_schema=GlobalState,
    checkpointer=checkpointer,
    prompt=system_prompt,
)


# Create chat sessions
def generate_session_uuid():
    thread_uuid = uuid.uuid4().hex
    print(f"------ New session uuid {thread_uuid} ----")
    return thread_uuid


if __name__ == "__main__":
    from rich.console import Console
    from rich.tree import Tree

    # BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # print(f"Project base directory: {BASE_DIR}")

    # Rich formatting
    console = Console()
    tree = Tree("[#FF66FA]> Search[/]")

    # Graph config
    graph_config = {
        "configurable": {"thread_id": ""},
        "recursion_limit": 50,
    }

    session_uuid = console.input("Enter a session uuid to resume conversation: ")
    if not session_uuid:
        session_uuid = generate_session_uuid()

    graph_config["configurable"].update({"thread_id": session_uuid})

    while True:
        user_input = console.input("[#69FFB4]> [/]")
        messages = [HumanMessage(content=user_input)]

        # ------ Run Agent ------
        running_agent = agent.stream(
            config=graph_config,
            input={"messages": messages},
            stream_mode="updates",
        )

        for chunk in running_agent:
            print(chunk)

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
        # print(running_agent.get_state(graph_config))

        human_approval = input("Enter Yes/No to accept/reject:")
        print("----- Resuming where graph stopped execution ----")

        running_agent = agent.stream(
            Command(resume={"option": human_approval}),
            config=graph_config,
            stream_mode="updates",
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


# Session uuids
# a66d406aace2442a8a335caad837e20e
