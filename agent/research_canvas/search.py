"""
The search node is responsible for searching the manual vectorstore for information.
"""

import os
from typing import cast, Optional
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage, ToolMessage
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings
from langchain.tools.retriever import create_retriever_tool
from copilotkit.langgraph import copilotkit_emit_state
from research_canvas.state import AgentState
from research_canvas.model import get_model

def create_tools(
    vectorstore: Optional[Chroma] = None,
    tool_name: str = "retrieve_manual_for_machine",
    tool_description: str = "Search and return issue support information for the MS2750 filleting machine."
) -> list:
    """
    Create and return the retriever tool from the vectorstore.
    
    Args:
        vectorstore: Optional pre-existing Chroma vectorstore
        tool_name: Name for the retriever tool
        tool_description: Description of what the tool does
        
    Returns:
        List containing the retriever tool
    """
        
    if vectorstore is None:
        raise Exception("No vectorstore provided")
        
    retriever = vectorstore.as_retriever()
    retriever_tool = create_retriever_tool(
        retriever,
        tool_name,
        tool_description,
    )
    return [retriever_tool]

# Initialize the vectorstore
vectorstore = Chroma(
    persist_directory="hw_and_sw_manual_vectorstore_2024_11_25/my_vectorstore",
    embedding_function=OpenAIEmbeddings(),
    collection_name="manual-collection"
)

# Create tools from existing vectorstore
tools = create_tools(vectorstore=vectorstore)

async def search_node(state: AgentState, config: RunnableConfig):
    """
    The search node is responsible for searching the manual vectorstore for relevant information.
    """
    ai_message = cast(AIMessage, state["messages"][-1])
    
    state["rag_results"] = state.get("rag_results", [])  # New key for RAG results
    state["resources"] = state.get("resources", [])
    state["logs"] = state.get("logs", [])
    queries = ai_message.tool_calls[0]["args"]["queries"]

    for query in queries:
        state["logs"].append({
            "message": f"Searching manual for: {query}",
            "done": False
        })

    await copilotkit_emit_state(config, state)

    search_results = []
    for i, query in enumerate(queries):
        # Use the retriever tool to get relevant documents
        response = tools[0].invoke({"query": query})
        search_results.append(response)
        state["logs"][i]["done"] = True
        await copilotkit_emit_state(config, state)

    # Add the search results to the RAG results instead of resources
    state["rag_results"].extend(search_results)
    
    state["messages"].append(ToolMessage(
        tool_call_id=ai_message.tool_calls[0]["id"],
        content=f"Found the following information in the manual: {search_results}"
    ))

    state["logs"] = []
    await copilotkit_emit_state(config, state)

    return state