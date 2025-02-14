"""
This module contains the implementation of the download_node function.
"""

from markitdown import MarkItDown
from openai import OpenAI
import extract_msg
import os
import aiohttp
import html2text
import atexit
from urllib.parse import urlparse
from copilotkit.langgraph import copilotkit_emit_state
from langchain_core.runnables import RunnableConfig
from research_canvas.state import AgentState

client = OpenAI()
md = MarkItDown(llm_client=client, llm_model="gpt-4o")  # This does not work for Mac Preview generated PDFs

_RESOURCE_CACHE = {}

def cleanup():
    """
    Cleanup function to be called on exit.
    Ensures all resources are properly released.
    """
    global client, md
    if client:
        client.close()
    _RESOURCE_CACHE.clear()

atexit.register(cleanup)

_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3" # pylint: disable=line-too-long

def get_resource(url: str):
    """
    Get a resource from the cache.
    """
    return _RESOURCE_CACHE.get(url, "")

def is_local_path(url: str) -> bool:
    """
    Check if the given URL is a local file path.
    """
    parsed = urlparse(url)
    return not parsed.scheme or parsed.scheme == 'file'

async def _read_local_file(path: str) -> str:
    """
    Read a local file and return its content.
    """
    try:
        _, ext = os.path.splitext(path.lower())
        
        if ext == '.msg':
            msg = extract_msg.openMsg(path)
            return msg.getJson()
        
        # For text-based files, read their content directly
        elif ext in ['.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.json']:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
                
        else:
            content = md.convert(path)
            return content.text_content
            
    except Exception as e:
        return f"Error reading local file: {e}"

async def _process_resource(url: str):
    """
    Download a resource from the internet or local file system asynchronously.
    """
    try:
        # Clean up the URL/path by removing extra quotes and normalizing path
        url = url.strip("'\"").replace("\\", "/")

        # Handle local files
        if is_local_path(url):
            return await _read_local_file(url)

        # Handle web URLs
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers={"User-Agent": _USER_AGENT},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as response:
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '').lower()
                
                # Handle PDFs and other binary content
                if 'application/pdf' in content_type or url.lower().endswith('.pdf'):
                    content = md.convert(url)
                    return content.text_content
                
                # Handle HTML content
                if 'text/html' in content_type:
                    html_content = await response.text()
                    return html2text.html2text(html_content)
                    
                # Handle plain text content
                if 'text/plain' in content_type:
                    return await response.text()
                    
                # For unknown content types, try md.convert
                content = md.convert(url)
                return content.text_content

    except Exception as e:  # pylint: disable=broad-except
        return f"Error accessing resource: {e}"

async def process_file_node(state: AgentState, config: RunnableConfig):
    """
    Process resources that require downloading or special handling.
    Skips RAG results which are stored separately in state["rag_results"].
    """
    state["resources"] = state.get("resources", [])
    state["logs"] = state.get("logs", [])
    resources_to_download = []

    logs_offset = len(state["logs"])

    # Find resources that are not downloaded
    for resource in state["resources"]:
        # Skip resources that don't have a URL (like RAG results)
        if not isinstance(resource, dict) or "url" not in resource:
            continue
            
        if not get_resource(resource["url"]):
            resources_to_download.append(resource)
            state["logs"].append({
                "message": f"Processing {resource['url']}",
                "done": False
            })

    # Emit the state to let the UI update
    await copilotkit_emit_state(config, state)

    # Download resources
    for i, resource in enumerate(resources_to_download):
        content = await _process_resource(resource["url"])
        _RESOURCE_CACHE[resource["url"]] = content
        resource["description"] = content
        
        # Find the index of this resource in the original resources list
        resource_index = state["resources"].index(resource)
        state["resources"][resource_index]["description"] = content
        state["logs"][logs_offset + i]["done"] = True

        await copilotkit_emit_state(config, state)
    return state
