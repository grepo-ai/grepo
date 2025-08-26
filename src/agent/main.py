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


from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage, AIMessage
from langchain_anthropic import ChatAnthropic


from agent.state import GlobalState


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
        }

    @property
    def config(self):
        return self._config

    @property
    def agent_state(self):
        return self._compiled_graph.get_state(self._config)

    @property
    def token_usage(self):
        return self._token_usage

    def get_messages(self):
        return self._compiled_graph.get_state(self._config).values.get("messages", [])

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
        # TODO: Complete compaction logic also ensure last message should be from AI which is a summary
        """
        Compaction automatically happens when the chat session is just about to reach context window size
        of a LLM then it takes all the messages in the session (agent state) and generates a high quality summary condensing it
        into a shorter and more concise version while keeping key insights and core points in this generated summary.

        NOTE: Compaction logic does not take into consideration system prompt or files added to current context as these
        are must to be kept in active context window.
        """

        def context_compaction(agent, token_store: dict):
            while True:
                token_store["total_input_tokens"] = 0
                token_store["total_output_tokens"] = 0
                token_store["cache_creation_input_tokens"] = 0
                token_store["cache_read_input_tokens"] = 0

                # Extract messages from agent state and count total tokens
                all_messages = agent.get_messages()

                for message in all_messages:
                    if message.response_metadata:
                        response_metadata = message.response_metadata["usage"]
                        token_store["total_input_tokens"] = response_metadata[
                            "input_tokens"
                        ]
                        token_store["total_output_tokens"] = response_metadata[
                            "output_tokens"
                        ]
                        token_store["cache_creation_input_tokens"] = response_metadata[
                            "cache_creation_input_tokens"
                        ]
                        token_store["cache_read_input_tokens"] = response_metadata[
                            "cache_read_input_tokens"
                        ]
                # TODO: Perform compaction if token usage in the session is just about to reach context window size

                # Poll every 30 secs and check if compaction is required
                time.sleep(30)

        if self.auto_compact:
            # Run compaction in background and poll every 30 secs
            compaction_thread = threading.Thread(
                target=context_compaction,
                kwargs={"agent": self, "token_store": self._token_usage},
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
        # else simply use the generator object to get stream updates
        return self._compiled_graph.stream(
            input=input, config=self._config, stream_mode=self.stream_mode
        )
