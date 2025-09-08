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
        self._token_usage: dict = None
        self._stop_thread = threading.Event()
        self._last_message_id = (-1, None)

    @property
    def config(self):
        return self._config

    @property
    def agent_state(self):
        return self._compiled_graph.get_state(self._config)

    @property
    def token_usage(self):
        return self._token_usage

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

    def format_state_messages(self, all_state_messages):
        formatted_messages = []

        # Calculate total tokens to check if compaction is needed
        for message in all_state_messages:
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
                            formatted_messages.append(f"<ai>{content['text']}<ai>")
                else:
                    formatted_messages.append(f"<ai>{message.content}</ai>")

            elif isinstance(message, ToolMessage):
                if message.content is not None and "Error:" not in message.content:
                    if isinstance(message.content, list):
                        tool_messages = ""

                        for tool_message in message.content:
                            if isinstance(tool_message, list):
                                for line in tool_message:
                                    tool_messages += str(line) + " "

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
                                            tool_messages += str(line) + " "

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

        return formatted_messages

    def session_cost(
        self, llm_client: LLMInterface, all_state_messages=None, compaction=False
    ):
        if all_state_messages is None:
            all_state_messages = self.get_messages()

        token_usage = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "session_cost": 0.00,
            "context_window_used": 0.0,
        }

        token_usage["total_input_tokens"] = 0
        token_usage["total_output_tokens"] = 0
        token_usage["cache_creation_input_tokens"] = 0
        token_usage["cache_read_input_tokens"] = 0

        # Calculate total tokens to check if compaction is needed
        for message in all_state_messages:
            if isinstance(message, AIMessage):
                response_metadata = message.response_metadata["usage"]
                token_usage["total_input_tokens"] += response_metadata["input_tokens"]
                token_usage["total_output_tokens"] += response_metadata["output_tokens"]
                token_usage["cache_creation_input_tokens"] += response_metadata[
                    "cache_creation_input_tokens"
                ]
                token_usage["cache_read_input_tokens"] += response_metadata[
                    "cache_read_input_tokens"
                ]

        total_tokens_used = (
            token_usage["total_input_tokens"]
            + token_usage["total_output_tokens"]
            + token_usage["cache_creation_input_tokens"]
            + token_usage["cache_read_input_tokens"]
        )

        cost_per_token = llm_client.cost_per_token

        final_total_cost = (
            token_usage["total_input_tokens"] * cost_per_token["input_token_cost"]
            + token_usage["total_output_tokens"] * cost_per_token["output_token_cost"]
            + token_usage["cache_creation_input_tokens"]
            * cost_per_token["cache_write_cost_5m"]
            + token_usage["cache_read_input_tokens"] * cost_per_token["cache_read_cost"]
        )

        token_usage["session_cost"] = f"${final_total_cost:.4f}"
        token_usage["context_window_used"] = (
            f"{(total_tokens_used / llm_client._context_window_size) * 100:.2f}%"
        )

        if not compaction:
            self._token_usage = token_usage

        return token_usage

    def calculate_cycle_cost(self, llm_client):
        "This method calculates cost of 1 complete agent loop i.e from human message to AI's final response"

        all_messages = self.get_messages()
        cost_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "cost": 0,
            "context_window_used": 0,
        }

        for index, message in enumerate(all_messages):
            if (
                isinstance(message, AIMessage)
                and index > self._last_message_id[0]
                and self._last_message_id[1] != message.id
            ):
                response_metadata = message.response_metadata["usage"]

                cost_stats["total_input_tokens"] += response_metadata["input_tokens"]
                cost_stats["total_output_tokens"] += response_metadata["output_tokens"]
                cost_stats["cache_creation_input_tokens"] += response_metadata[
                    "cache_creation_input_tokens"
                ]
                cost_stats["cache_read_input_tokens"] += response_metadata[
                    "cache_read_input_tokens"
                ]

                self._last_message_id = (index, message.id)

        # Calculate cost (in $) and context window (%) used for this cycle
        total_tokens_used = (
            cost_stats["total_input_tokens"]
            + cost_stats["total_output_tokens"]
            + cost_stats["cache_creation_input_tokens"]
            + cost_stats["cache_read_input_tokens"]
        )

        cost_per_token = llm_client.cost_per_token

        final_total_cost = (
            cost_stats["total_input_tokens"] * cost_per_token["input_token_cost"]
            + cost_stats["total_output_tokens"] * cost_per_token["output_token_cost"]
            + cost_stats["cache_creation_input_tokens"]
            * cost_per_token["cache_write_cost_5m"]
            + cost_stats["cache_read_input_tokens"] * cost_per_token["cache_read_cost"]
        )

        cost_stats["cost"] = f"${final_total_cost:.4f}"
        cost_stats["context_window_used"] = (
            f"{(total_tokens_used / llm_client._context_window_size) * 100:.2f}%"
        )

        return cost_stats

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
                # Get all messages in agent state
                all_messages = agent.get_messages()

                formatted_messages = agent.format_state_messages(all_messages)

                # Calculate cost (in $) of session and context (%) used so far
                token_usage = agent.session_cost(
                    llm_client, all_messages, compaction=True
                )

                # TODO: Check if cache_read/ cache_create tokens are counted in context window
                session_context_size = (
                    token_usage["total_input_tokens"]
                    + token_usage["cache_creation_input_tokens"]
                    + token_usage["cache_read_input_tokens"]
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

                        # TODO: Handle case when new messages might arrive while compaction is happening and we have not added those
                        # messages in the summary payload also handle case while performing a re-write of the message history we add
                        # new messages as it is to the agent state that might get lost during a re-write.

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
