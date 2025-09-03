import os
import glob
import re
import uuid
import json
import time
import threading
from typing import Annotated, Union, Optional
from typing_extensions import TypedDict


from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import RemoveMessage
from langchain_core.tools.base import BaseTool
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.checkpoint.sqlite import SqliteSaver


from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_anthropic import ChatAnthropic


from agent.state import GlobalState
from agent.llm import LLMInterface


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
        auto_compact: bool = False,
    ):
        self.model: Union[ChatAnthropic, None] = model
        self.system_prompt: SystemMessage = system_prompt
        self.tools: list[BaseTool] = tools
        self.state_schema: GlobalState = schema
        self.stream_mode: Optional[list[str]] = stream_mode
        self.checkpointer: SqliteSaver = checkpointer
        self._config: dict = config
        self._compiled_graph: CompiledStateGraph = None
        self.auto_compact: bool = auto_compact
        self._token_usage: dict = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "session_cost": 0.00,
            "used_context_window_percent": 0.0,
        }
        self._stop_thread = threading.Event()

    @property
    def config(self):
        return self._config

    @property
    def agent_state(self):
        return self._compiled_graph.get_state(self._config)

    @property
    def token_usage(self):
        return self._token_usage

    def session_cost_stats(self, llm_client: LLMInterface):
        cost_per_token = llm_client.cost_per_token

        total_tokens_used = (
            self._token_usage["total_input_tokens"]
            + self._token_usage["total_output_tokens"]
        )

        self._token_usage["session_cost"] = f"${total_tokens_used * cost_per_token:.4f}"
        self._token_usage["used_context_window_percent"] = (
            f"{(total_tokens_used / 200000) * 100:.2f}%"
        )

    def stop_thread(self):
        self._stop_thread.set()

    def get_messages(self):
        return self._compiled_graph.get_state(self._config).values.get("messages", [])

    def update_messages(self, messages, compact=False):
        if compact:
            new_messages = [RemoveMessage(id=REMOVE_ALL_MESSAGES), *messages]

        self._compiled_graph.update_state(self._config, {"messages": new_messages})

    def clear_session(
        self,
    ):
        self._compiled_graph.update_state(
            self._config,
            {
                "messages": [
                    RemoveMessage(id=REMOVE_ALL_MESSAGES),
                    HumanMessage(content="hi"),
                ]
            },
        )

    def auto_compact_context(self):
        """
        Compaction automatically happens when the chat session is just about to reach context window size
        of a LLM then it takes all the messages in the active session (agent state) and generates a high quality summary condensing it
        into a shorter and more concise version while keeping key insights and core points in this generated summary.

        NOTE: Compaction logic does not take into consideration system prompt or files added to current context as these
        are must to be kept in active context window at all times.
        """

        def context_compaction(agent):
            llm_client = LLMInterface()

            while not agent._stop_thread.is_set():
                agent._token_usage["total_input_tokens"] = 0
                agent._token_usage["total_output_tokens"] = 0
                agent._token_usage["cache_creation_input_tokens"] = 0
                agent._token_usage["cache_read_input_tokens"] = 0

                all_messages = agent.get_messages()

                formatted_messages = []

                # Calculate total tokens to check if compaction is needed
                for message in all_messages:
                    if isinstance(message, AIMessage):
                        response_metadata = message.response_metadata["usage"]
                        agent._token_usage["total_input_tokens"] += response_metadata[
                            "input_tokens"
                        ]
                        agent._token_usage["total_output_tokens"] += response_metadata[
                            "output_tokens"
                        ]
                        agent._token_usage["cache_creation_input_tokens"] = (
                            response_metadata["cache_creation_input_tokens"]
                        )
                        agent._token_usage["cache_read_input_tokens"] = (
                            response_metadata["cache_read_input_tokens"]
                        )

                    # Format messages for generating a summary
                    if isinstance(message, HumanMessage):
                        formatted_messages.append(f"<human>{message.content}</human>")

                    elif isinstance(message, AIMessage):
                        if isinstance(message.content, list):
                            for content in message.content:
                                if (
                                    content.get("text") is not None
                                    and content.get("type") == "text"
                                ):
                                    formatted_messages.append(
                                        f"<ai>{content['text']}<ai>"
                                    )
                        else:
                            formatted_messages.append(f"<ai>{message.content}</ai>")

                    elif isinstance(message, ToolMessage):
                        if (
                            message.content is not None
                            and "Error:" not in message.content
                        ):
                            if isinstance(message.content, list):
                                tool_messages = ""

                                for tool_message in message.content:
                                    if isinstance(tool_message, list):
                                        for line in tool_message:
                                            tool_messages += line + " "

                                    else:
                                        tool_messages += tool_message + " "

                                formatted_messages.append(
                                    f"<tool> Tool name: {message.name}\n Tool response:{tool_messages} </tool>"
                                )

                            else:
                                try:
                                    message_json_content = json.loads(message.content)

                                    if isinstance(message_json_content, list):
                                        tool_messages = ""

                                        for tool_message in message_json_content:
                                            if isinstance(tool_message, list):
                                                for line in tool_message:
                                                    tool_messages += line + " "

                                            else:
                                                tool_messages += tool_message + " "

                                        formatted_messages.append(
                                            f"<tool> Tool name: {message.name}\n Tool response:{tool_messages} </tool>"
                                        )

                                # Type of message content is str
                                except json.JSONDecodeError:
                                    formatted_messages.append(
                                        f"<tool> Tool name: {message.name}\n Tool response:{message.content} </tool>"
                                    )
                                    pass

                # Calculate cost ($) of session and context (%) used so far
                agent.session_cost_stats(llm_client)

                session_context_size = (
                    agent._token_usage["total_input_tokens"]
                    + agent._token_usage["total_output_tokens"]
                )

                # TODO: Replace 10k by actual context window size but minus 20K avoid context bloating
                if session_context_size > 10000:
                    print("------ Attempting Compaction -----")
                    # Compact only when agent loop has ended and there are no tool calls remaining
                    last_message = agent.get_messages()[-1]

                    # TODO: Verify if this condition is correct whether last message is always AIMessage instance or not?
                    if (
                        isinstance(last_message, AIMessage)
                        and not last_message.tool_calls
                    ):
                        generated_summary = llm_client.generate_summary(
                            "\n".join(formatted_messages)
                        )

                        # Rewrite the message history and update with a summary
                        agent.update_messages(
                            messages=[
                                HumanMessage(
                                    content="Generate a summary of the entire conversation."
                                ),
                                generated_summary,
                            ],
                            compact=True,
                        )
                        print("------ Compaction Completed ------")

                # Poll every 10 secs and check if compaction is required (keeping it time based for now to simply logic)
                time.sleep(10)

        if self.auto_compact:
            # Run compaction in background thread
            compaction_thread = threading.Thread(
                target=context_compaction,
                kwargs={"agent": self},
                daemon=True,
            )
            compaction_thread.start()

    def _create(self):
        self._compiled_graph = create_react_agent(
            self.model,
            tools=self.tools,
            state_schema=self.state_schema,
            checkpointer=self.checkpointer,
            prompt=self.system_prompt,
        )

        # Run auto-compaction in background
        self.auto_compact_context()

        return self._compiled_graph

    def stream(self, input):
        # Returns a new generator on each new invocation of user input
        # simply iterate over generator object to get stream updates
        return self._compiled_graph.stream(
            input=input, config=self._config, stream_mode=self.stream_mode
        )
