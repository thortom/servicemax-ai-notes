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
import re

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
    persist_directory="hw_and_sw_manual_vectorstore_2025_02_07/my_vectorstore",
    embedding_function=OpenAIEmbeddings(),
    collection_name="manual-collection"
)

# Create tools from existing vectorstore
tools = create_tools(vectorstore=vectorstore)

def extract_error_code(query: str) -> Optional[str]:
    """
    Extract error code from query if present.
    Handles both standard error codes (e.g., F6003) and hexadecimal codes (e.g., 0x01010006).
    """
    # Pattern for standard error codes like F6003
    standard_pattern = r'[A-Z]\d{4}'
    # Pattern for hexadecimal error codes like 0x01010006
    hex_pattern = r'0x[0-9A-Fa-f]{8}'
    
    # Try standard pattern first
    match = re.search(standard_pattern, query)
    if match:
        return match.group(0)
    
    # Try hex pattern if standard pattern didn't match
    match = re.search(hex_pattern, query)
    if match:
        return match.group(0)
    
    return None

async def search_node(state: AgentState, config: RunnableConfig):
    """
    The search node performs both error code specific search and general semantic search,
    combining results from both approaches when an error code is present.
    """
    ai_message = cast(AIMessage, state["messages"][-1])
    
    state["rag_results"] = state.get("rag_results", [])
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
    seen_contents = set()  # Track unique content
    
    for i, query in enumerate(queries):
        combined_results = []
        error_code = extract_error_code(query)
        
        # If error code is present, do error code specific search first
        if error_code:
            try:
                # Search specifically in motor error codes using metadata with proper operator syntax
                error_results = vectorstore.similarity_search(
                    query,
                    k=2,
                    filter={
                        "$and": [
                                {"error_code": {"$eq": error_code}},
                                {"source": {"$eq": "motor_error_codes"}}
                        ]
                    }
                )
                if error_results:
                    # Only add unique content
                    for doc in error_results:
                        if doc.page_content not in seen_contents:
                            combined_results.append(doc.page_content)
                            seen_contents.add(doc.page_content)
                    state["logs"].append({
                        "message": f"Found specific error code match for {error_code}",
                        "done": True
                    })
            except Exception as e:
                state["logs"].append({
                    "message": f"Error in error code search: {str(e)}",
                    "done": True
                })
        
        # Always perform general semantic search
        try:
            # For general search, exclude motor error codes to avoid duplication
            general_filter = {"source": {"$ne": "motor_error_codes"}} if error_code else None
            general_results = vectorstore.similarity_search(
                query,
                k=3,
                filter=general_filter
            )
            
            # Only add unique content
            for doc in general_results:
                if doc.page_content not in seen_contents:
                    combined_results.append(doc.page_content)
                    seen_contents.add(doc.page_content)
                
        except Exception as e:
            # Fallback to using the retriever tool if metadata filtering fails
            general_results = tools[0].invoke({"query": query})
            if not combined_results:  # Only use if we don't have error results
                for content in general_results:
                    if content not in seen_contents:
                        combined_results.append(content)
                        seen_contents.add(content)
        
        if combined_results:  # Only append if we have results
            search_results.append(combined_results)
        state["logs"][i]["done"] = True
        await copilotkit_emit_state(config, state)

    state["rag_results"].extend(search_results)
    
    state["messages"].append(ToolMessage(
        tool_call_id=ai_message.tool_calls[0]["id"],
        content=f"Found the following information in the manual: {search_results}"
    ))

    state["logs"] = []
    await copilotkit_emit_state(config, state)

    return state