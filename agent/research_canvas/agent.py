"""
This is the main entry point for the AI.
It defines the workflow graph and the entry point for the agent.
"""
import getpass

# pylint: disable=line-too-long, unused-import
import os


def _set_env(var: str):
    if not os.environ.get(var):
        os.environ[var] = getpass.getpass(f"{var}: ")


_set_env("OPENAI_API_KEY")
_set_env("LANGCHAIN_API_KEY")
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "fresh-servicemax"

from langchain_core.messages import AIMessage, ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from research_canvas.state import AgentState
from research_canvas.process_file import process_file_node
from research_canvas.chat import chat_node
from research_canvas.search import search_node
from research_canvas.delete import delete_node, perform_delete_node

# Define a new graph
workflow = StateGraph(AgentState)
workflow.add_node("process_file", process_file_node)
workflow.add_node("chat_node", chat_node)
workflow.add_node("search_node", search_node)
workflow.add_node("delete_node", delete_node)
workflow.add_node("perform_delete_node", perform_delete_node)


memory = MemorySaver()
workflow.set_entry_point("process_file")
workflow.add_edge("process_file", "chat_node")
workflow.add_edge("delete_node", "perform_delete_node")
workflow.add_edge("perform_delete_node", "chat_node")
workflow.add_edge("search_node", "process_file")
graph = workflow.compile(checkpointer=memory, interrupt_after=["delete_node"])
