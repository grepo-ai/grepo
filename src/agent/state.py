import os
import glob
import re
from typing import Annotated
from typing_extensions import TypedDict


from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langgraph.prebuilt.chat_agent_executor import AgentState

from operator import add


class GlobalState(AgentState):
    # edit_file_permissions: bool
    changed_code: Annotated[list[tuple], add]
