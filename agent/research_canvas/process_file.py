"""
This module contains the implementation of the download_node function.
"""

from markitdown import MarkItDown
from openai import OpenAI
import extract_msg
from copilotkit.langgraph import copilotkit_emit_state
from langchain_core.runnables import RunnableConfig
from research_canvas.state import AgentState

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")

_RESOURCE_CACHE = {}

def get_resource(url: str):
    """
    Get a resource from the cache.
    """
    return _RESOURCE_CACHE.get(url, "")


_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3" # pylint: disable=line-too-long

async def _process_resource(url: str):
    """
    Download a resource from the internet asynchronously.
    """
    try:
        # Clean up the URL/path by removing extra quotes and normalizing path
        url = url.strip("'\"").replace("\\", "")
        
        if url.lower().endswith(".msg"):    # TODO: Do this asynchronously
            msg = extract_msg.openMsg(url)
            # Process MSG file content
            content = f"Subject: {msg.subject}\nBody: {msg.body}"
            summary = md.getJson(content)
            print(f"url msg: {url}")
            print(summary)
            return summary

        else:
            content = md.convert(url)
            summary = content.text_content
            print(f"url other: {url}")
            print(summary)
            return summary
    except Exception as e: # pylint: disable=broad-except
        _RESOURCE_CACHE[url] = "ERROR"
        return f"Error processing resource: {e}"

async def process_file_node(state: AgentState, config: RunnableConfig):
    """
    Download resources from the internet.
    """
    state["resources"] = state.get("resources", [])
    state["logs"] = state.get("logs", [])
    resources_to_download = []

    logs_offset = len(state["logs"])

    # Find resources that are not downloaded
    for resource in state["resources"]:
        if not get_resource(resource["url"]):
            resources_to_download.append(resource)
            state["logs"].append({
                "message": f"Downloading {resource['url']}",
                "done": False
            })

    # Emit the state to let the UI update
    await copilotkit_emit_state(config, state)

    # Download the resources
    for i, resource in enumerate(resources_to_download):
        # Update the resource description and ensure state is properly updated
        description = await _process_resource(resource["url"])
        resource["description"] = description
        state["resources"][i]["description"] = description  # Update the state's resources directly
        state["logs"][logs_offset + i]["done"] = True

        # update UI
        await copilotkit_emit_state(config, state)

    return state
