import os
import json
import time
import threading
from typing import Union, Optional
from collections import deque
from pathlib import Path


from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import RemoveMessage
from langchain_core.tools.base import BaseTool
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command


from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, ToolMessage
from langchain_anthropic import ChatAnthropic


from agent.state import GlobalState
from agent.llm import LLMInterface


from rich.console import Console
from rich.tree import Tree
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style


# ---- Langfuse ---
from agent.tracing import langfuse_handler


from agent.tools import (
    list_files,
    read_file,
    grep,
    edit_file,
    get_code_block,
    glob,
    write,
)
from agent.utils import (
    get_checkpointer,
    construct_code,
    format_grep_results,
)
from src.cli.utils import code_block_md_theme, color_palette


class Agent:
    def __init__(
        self,
        root_dir: str,
        model: str,
        provider: str,
        output_queue: deque,
        tools: list,
        schema: GlobalState,
        checkpointer: SqliteSaver,
        session_uuid: str,
        stream_mode: Union[str, list],
        config: dict = {},
        auto_compact: bool = False,
    ):
        self.llm_client = LLMInterface(model=model, llm_provider=provider)
        self.model_interface: Union[ChatAnthropic, None] = self.llm_client.client()
        self.system_prompt: SystemMessage = self._get_system_prompt(root_dir)
        self.tools: list[BaseTool] = tools
        self.state_schema: GlobalState = schema
        self.stream_mode: Optional[list[str]] = stream_mode
        self.checkpointer: SqliteSaver = checkpointer
        self.session_uuid = session_uuid
        self._config: dict = config if config else self._get_config()
        self._compiled_graph: CompiledStateGraph = None
        self.auto_compact: bool = auto_compact
        self._cycle_stats: dict = None
        self._stop_thread = threading.Event()
        self._last_message_id = (-1, None)
        self._output_queue = output_queue
        self._ui_renders = {}

    def _get_system_prompt(self, root_dir):
        agents_md_path = f"{root_dir}/AGENTS.md"
        user_prompt_guidelines = ""

        if os.path.exists(agents_md_path):
            user_prompt_guidelines = Path(agents_md_path).read_text(encoding="utf-8")

        self.system_prompt = self.llm_client.get_system_prompt(
            user_prompt=user_prompt_guidelines
        )

    @property
    def config(self):
        return self._config

    def _get_config(self):
        return {
            "configurable": {"thread_id": self.session_uuid},
            "recursion_limit": 50,
            "callbacks": [langfuse_handler],
        }

    @property
    def thinking(self):
        return self.model_interface.thinking

    @thinking.setter
    def thinking(self, flag: bool):
        if flag:
            setattr(
                self.model_interface,
                "thinking",
                {"type": "enabled", "budget_tokens": 2000},
            )
        else:
            setattr(self.model_interface, "thinking", None)

    @property
    def agent_state(self):
        return self._compiled_graph.get_state(self._config)

    @property
    def cycle_stats(self):
        return self._cycle_stats

    @cycle_stats.setter
    def cycle_stats(self, stats_dict):
        self._cycle_stats = stats_dict

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

        for message in all_state_messages:
            # Format messages for generating a summary
            if isinstance(message, HumanMessage):
                formatted_messages.append(
                    f"<human query>{message.content}</human query>"
                )

            elif isinstance(message, AIMessage):
                if isinstance(message.content, list):
                    for content in message.content:
                        if (
                            content.get("text") is not None
                            and content.get("type") == "text"
                        ):
                            formatted_messages.append(
                                f"<ai response>{content['text']}</ai response>"
                            )

                        if content.get("type") == "tool_use":
                            tool_message = ""
                            for tool_call in message.tool_calls:
                                tool_message += (
                                    f"<tool call>tool_name: {tool_call['name']} -- "
                                )
                                for key, value in tool_call["args"].items():
                                    tool_message += (
                                        f"arg_name:{key},arg_value:{value}\n"
                                    )
                            tool_message += " </tool call>"
                            formatted_messages.append(tool_message)

                else:
                    formatted_messages.append(
                        f"<ai response>{message.content}</ai response>"
                    )

            elif isinstance(message, ToolMessage):
                # Successful tool call response
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
                            f"<tool response> Tool name: {message.name}\n Tool response:{tool_messages} </tool response>"
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
                                    f"<tool response> Tool name: {message.name}\n Tool response:{tool_messages} </tool response>"
                                )

                        # Type of message content is str
                        except json.JSONDecodeError:
                            formatted_messages.append(
                                f"<tool response> Tool name: {message.name}\n Tool response:{message.content} </tool response>"
                            )
                            pass

                # Error tool call response
                elif message.content is not None and "Error:" in message.content:
                    formatted_messages.append(
                        f"<tool response> Tool name: {message.name}\n Tool response:{message.content} </tool response>"
                    )

        return formatted_messages

    def session_cost(self, compaction=False):
        all_state_messages = self.get_messages()
        llm_client = self.llm_client

        token_usage = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "session_cost": 0.00,
            "context_window_used": 0.0,
            "model_used": llm_client.get_model_name(llm_client.model),
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

        return token_usage

    def calculate_cycle_cost(self, all_messages=None, render=False):
        "This method calculates cost of 1 complete agent loop i.e from human message to AI's final response"

        llm_client = self.llm_client

        if all_messages is None:
            all_messages = self.get_messages()

        cost_stats = {
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens": 0,
            "cost": 0,
            "context_window_used": 0,
            "model_used": llm_client.get_model_name(llm_client.model),
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

        self._cycle_stats = cost_stats

        # Format the final cost usage stats to renderable fortmat
        if render:
            usage_stats_keys = {
                "total_input_tokens": "↑",
                "total_output_tokens": "↓",
                "cost": "",
            }

            renderable_cost_stats = "\n"
            for key, value in self._cycle_stats.items():
                if key in [
                    "cache_creation_input_tokens",
                    "cache_read_input_tokens",
                    "model_used",
                    "context_window_used",
                ]:
                    continue
                renderable_cost_stats += f"{usage_stats_keys.get(key)} {value} "

            return f"[dim]{Text(renderable_cost_stats, (0, 0, 0, 1))}[/]"

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
                cycle_cost = agent.cycle_stats
                if not cycle_cost:
                    continue

                session_context_size = (
                    cycle_cost["total_input_tokens"]
                    + cycle_cost["total_output_tokens"]
                    + cycle_cost["cache_creation_input_tokens"]
                    + cycle_cost["cache_read_input_tokens"]
                )

                # TODO: Replace 10k by actual context window size but minus 20K avoid context bloating
                if session_context_size > 10000 or float(
                    cycle_cost["context_window_used"][:-1]
                ) >= float(f"{95:.2f}"):
                    print("---- cycle costs before compaction ----")
                    print(cycle_cost)
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

                        # Reset the last message index (TODO: Check Linear ticket GREP-56)
                        agent._last_message_id = (-1, None)
                        print("------ Compaction Completed ------")

                        # Update the cost stats after compaction
                        cost_stats = {
                            "total_input_tokens": generated_summary.response_metadata[
                                "usage"
                            ]["input_tokens"],
                            "total_output_tokens": generated_summary.response_metadata[
                                "usage"
                            ]["output_tokens"],
                            "cache_creation_input_tokens": generated_summary.response_metadata[
                                "usage"
                            ]["cache_creation_input_tokens"],
                            "cache_read_input_tokens": generated_summary.response_metadata[
                                "usage"
                            ]["cache_read_input_tokens"],
                            "cost": 0,
                            "context_window_used": 0,
                        }

                        cost_per_token = llm_client.cost_per_token

                        final_total_cost = (
                            cost_stats["total_input_tokens"]
                            * cost_per_token["input_token_cost"]
                            + cost_stats["total_output_tokens"]
                            * cost_per_token["output_token_cost"]
                            + cost_stats["cache_creation_input_tokens"]
                            * cost_per_token["cache_write_cost_5m"]
                            + cost_stats["cache_read_input_tokens"]
                            * cost_per_token["cache_read_cost"]
                        )

                        cost_stats["cost"] = f"${final_total_cost:.4f}"

                        # Calculate cost (in $) and context window (%) used for this cycle
                        total_tokens_used = (
                            cost_stats["total_input_tokens"]
                            + cost_stats["total_output_tokens"]
                            + cost_stats["cache_creation_input_tokens"]
                            + cost_stats["cache_read_input_tokens"]
                        )

                        cost_stats["context_window_used"] = (
                            f"{(total_tokens_used / llm_client._context_window_size) * 100:.2f}%"
                        )
                        agent.cycle_stats = cost_stats
                        print("------ cycle costs after compaction ------")
                        print(agent.cycle_stats)

                # Poll every 5 secs and check if compaction is required (keeping it time based for now to simplify logic)
                time.sleep(5)

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
            self.model_interface,
            tools=self.tools,
            state_schema=self.state_schema,
            checkpointer=self.checkpointer,
            prompt=self.system_prompt,
        )

        # Run auto-compaction in background
        self.auto_compact_context()

        # --- Text formatting ---
        console = Console()
        tree_grep = Tree("[#7CFCA7]● Search[/]")
        tree_list = Tree("[#7CFCA7]● List[/]")
        tree_read = Tree("[#7CFCA7]● Read[/]")
        tree_write = Tree("[#7CFCA7]● Write[/]")
        tree_code_block = Tree("[#7CFCA7]● Code[/]")

        self._ui_renders["console"] = console
        self._ui_renders["tree_list"] = tree_list
        self._ui_renders["tree_grep"] = tree_grep
        self._ui_renders["tree_read"] = tree_read
        self._ui_renders["tree_write"] = tree_write
        self._ui_renders["tree_code_block"] = tree_code_block

        return self._compiled_graph

    def stream(self, input):
        # Returns a new generator on each new invocation of user input
        # simply iterate over generator object to get stream updates
        return self._compiled_graph.stream(
            input=input, config=self._config, stream_mode=self.stream_mode
        )

    def invoke(
        self,
        renderable_splits,
        human_input,
    ):
        agent = self

        # TODO: Add Trees for edit file and glob tools
        console = self._ui_renders["console"]
        tree_list = self._ui_renders["tree_list"]
        tree_grep = self._ui_renders["tree_grep"]
        tree_read = self._ui_renders["tree_read"]
        tree_write = self._ui_renders["tree_write"]
        tree_code_block = self._ui_renders["tree_code_block"]

        messages = [HumanMessage(content=human_input)]

        # --- while loop ensures we have ended one complete cycle of agent inovcation ---
        input_type = {"messages": messages}
        agent_cycle_active = True

        while agent_cycle_active:
            renderable_splits.update_spinner(spin_it=True)

            running_agent = agent.stream(
                input=input_type,
            )

            for stream_message in running_agent:
                # Stream chunk type 1: Agent response
                if stream_message.get("agent"):
                    ai_messages = stream_message["agent"]["messages"][0].content

                    if isinstance(ai_messages, list):
                        for msg in ai_messages:
                            if msg.get("thinking"):
                                self._output_queue.append(
                                    (
                                        f"[dim]Thinking -> {msg['thinking']}[/]\n",
                                        console,
                                    )
                                )

                            elif msg.get("text"):
                                self._output_queue.append((f"{msg['text']}", console))
                    else:
                        markdown_text = Markdown(
                            ai_messages, code_theme=code_block_md_theme
                        )
                        self._output_queue.append((markdown_text, console))

                # Stream chunk type 2: Tool response
                elif stream_message.get("tools"):
                    # Check type of tool and populate tree alerts accordingly
                    tool_name = stream_message["tools"]["messages"][0].name
                    tool_message = stream_message["tools"]["messages"][0].content

                    # Tool: List files
                    if tool_name == "list_files" or "Error:" in tool_message:
                        tree_list.add("[#FA5CB3]Analysing files and directories...[/]")
                        self._output_queue.append((tree_list, console))

                    # Tool: Read file
                    elif tool_name == "read_file":
                        if tool_message is None:
                            continue

                        if "Error:" in tool_message:
                            tree_read.add(f"[#F76363]({tool_message})[/]")
                            self._output_queue.append((tree_read, console))
                            continue

                        read_file_data = json.loads(tool_message)
                        code_snippet, file_path = construct_code(
                            read_file_data, truncate=True
                        )

                        tree_read.add(
                            Text(
                                file_path,
                                style=Style(
                                    underline=False,
                                    color=color_palette["light-purple"],
                                ),
                            )
                        )
                        self._output_queue.append((tree_read, console))

                    # Tool: Grep
                    elif tool_name == "grep":
                        if not tool_message:
                            continue

                        if "Error:" in tool_message:
                            tree_read.add(f"[#F76363]({tool_message})[/]")
                            self._output_queue.append((tree_read, console))
                            continue

                        grep_content_list = json.loads(tool_message)
                        formatted_grep_results = format_grep_results(grep_content_list)

                        sub_tree_grep = Tree(
                            f"[#FA5CB3]Matches found ({len(formatted_grep_results)})[/]"
                        )
                        tree_grep.add(sub_tree_grep)
                        for res in formatted_grep_results:
                            file_link = f"vscode://file/{res[0]}{res[1]}"
                            sub_tree_grep.add(
                                Text(
                                    f"{res[0]}{res[1]}",
                                    style=Style(
                                        link=file_link,
                                        underline=False,
                                        color=color_palette["light-purple"],
                                    ),
                                )
                            )

                        self._output_queue.append((tree_grep, console))

                    # Tool: Get Code Definition
                    elif tool_name == "get_code_block":
                        if "Error:" in tool_message:
                            continue

                        self._output_queue.append((tree_code_block, console))
                        tree_code_block.add(
                            Syntax(
                                tool_message,
                                "python",
                                theme=code_block_md_theme,
                                background_color="default",
                            )
                        )
                        self._output_queue.append((tree_code_block, console))

                    # Tool: Write
                    elif tool_name == "write":
                        if "Error:" in tool_message:
                            continue
                        # TODO: --- Complete the logic ---

                # Stream chunk type 3: Interrupt response
                elif stream_message.get("__interrupt__"):
                    old_code = stream_message["__interrupt__"][0].value["old_code"]
                    new_code = stream_message["__interrupt__"][0].value["new_code"]
                    self._output_queue.append((old_code, console))

                    self._output_queue.append(
                        ("[#CFCFCF]----------Code Diff------------[/]", console)
                    )

                    self._output_queue.append((new_code, console))

                    human_approval = console.input("Enter Yes/No to accept/reject:")

                    input_type = Command(resume={"option": human_approval})

            # After the stream completes, check if we should continue the agent loop
            # The stream exhaustion means one complete react cycle has finished
            all_messages = agent.get_messages()

            if not all_messages:
                # No messages at all - should not happen, terminate
                agent_cycle_active = False
                continue

            # Find the last AI message
            last_ai_message = None
            for msg in reversed(all_messages):
                if isinstance(msg, AIMessage):
                    last_ai_message = msg
                    break

            if last_ai_message is None:
                # No AI message found - terminate to be safe
                agent_cycle_active = False
                continue

            # Check stop reason and tool calls
            stop_reason = last_ai_message.response_metadata.get("stop_reason", None)
            has_tool_calls = (
                hasattr(last_ai_message, "tool_calls")
                and last_ai_message.tool_calls
                and len(last_ai_message.tool_calls) > 0
            )

            # The agent loop should continue only if:
            # - stop_reason is NOT "end_turn", OR
            # - There are pending tool calls that haven't been executed
            # Since we use stream mode "updates", tool calls are auto-executed by the graph
            # So if stream ended and we have end_turn with no tool_calls, we're done
            if stop_reason == "end_turn" and not has_tool_calls:
                agent_cycle_active = False
            else:
                # Continue the loop - there might be more work to do
                agent_cycle_active = True

        renderable_splits.update_spinner(
            spin_it=False, data=agent.calculate_cycle_cost(render=True)
        )
        renderable_splits.renderable_data = agent.session_cost()


def initiate_agent(
    root_dir: str,
    session_uuid: str,
    output_queue: deque,
    model_provider: str,
    model: str,
):
    # --- Create an Agent ---
    agent = Agent(
        root_dir=root_dir,
        model=model,
        provider=model_provider,
        tools=[list_files, read_file, grep, edit_file, get_code_block, glob, write],
        schema=GlobalState,
        checkpointer=get_checkpointer(),
        stream_mode="updates",
        auto_compact=True,
        output_queue=output_queue,
        session_uuid=session_uuid,
    )

    agent._create()

    return agent
