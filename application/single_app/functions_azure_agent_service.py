"""
Lightweight Azure Agent Service integration for SimpleChat.

Reads configuration from environment variables by default and provides a thin
wrapper to invoke an Azure AI Foundry Agent using DefaultAzureCredential.

Required environment variables (unless passed explicitly):
 - AZURE_AI_FOUNDRY_ENDPOINT (e.g., https://myproj.eastus2.inference.ai.azure.com)
 - AZURE_AI_FOUNDRY_PROJECT  (project name)
 - AZURE_AI_FOUNDRY_AGENT_ID (agent GUID or name)
"""

from typing import List, Dict, Tuple, Any, Optional
import os

# Imports are deferred inside the function to avoid hard failures
# when the optional package isn't installed yet.


def invoke_azure_agent_service(
    messages: List[Dict[str, str]],
    *,
    project_name: Optional[str] = None,
    agent_name_or_id: Optional[str] = None,
    endpoint: Optional[str] = None,
) -> Tuple[str, Any]:
    """
    Invoke an Azure AI Foundry Agent and return (assistant_text, raw_response).

    Parameters:
      - messages: [{"role": "user|assistant|system", "content": "..."}, ...]
      - project_name: Optional override for AZURE_AI_FOUNDRY_PROJECT
      - agent_name_or_id: Optional override for AZURE_AI_FOUNDRY_AGENT_ID
      - endpoint: Optional override for AZURE_AI_FOUNDRY_ENDPOINT

    Returns:
      - (assistant_text, response)
    """
    endpoint = endpoint or os.getenv("AZURE_AI_FOUNDRY_ENDPOINT")
    project_name = project_name or os.getenv("AZURE_AI_FOUNDRY_PROJECT")
    agent_name_or_id = agent_name_or_id or os.getenv("AZURE_AI_FOUNDRY_AGENT_ID")

    if not endpoint or not project_name or not agent_name_or_id:
        raise ValueError(
            "Missing Azure Agent Service configuration. Set AZURE_AI_FOUNDRY_ENDPOINT, "
            "AZURE_AI_FOUNDRY_PROJECT, and AZURE_AI_FOUNDRY_AGENT_ID or pass overrides."
        )

    try:
        from azure.identity import DefaultAzureCredential
        from azure.ai.projects import AIProjectsClient
    except Exception as ex:
        raise ImportError(
            "azure-ai-projects (and azure-identity) is required to use Azure Agent Service. "
            "Install it via 'pip install azure-ai-projects azure-identity'."
        ) from ex

    credential = DefaultAzureCredential()
    client = AIProjectsClient(endpoint=endpoint, credential=credential)

    # Call the agent
    response = client.agents.invoke(
        project_name=project_name,
        agent_name=agent_name_or_id,
        input={"messages": messages},
    )

    # Try to extract the last assistant message
    assistant_text = None
    try:
        msgs = response.output.get("messages") if hasattr(response, "output") else None
        if isinstance(msgs, list) and msgs:
            # Prefer the last message content
            assistant_text = msgs[-1].get("content")
    except Exception:
        assistant_text = None

    if not assistant_text:
        assistant_text = str(response)

    return assistant_text, response
