import os
import glob
import re
from typing import Annotated
from typing_extensions import TypedDict


from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langgraph.prebuilt.chat_agent_executor import AgentState

from operator import add


class GlobalState(AgentState):
    changed_code: Annotated[list[tuple], add]
