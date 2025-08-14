"""
Lightweight Azure Agent Service integration for SimpleChat.

Reads configuration from environment variables and provides a thin
wrapper to invoke an Azure AI Foundry Agent using Azure service principal authentication.

Required environment variables:
 - AZURE_AI_FOUNDRY_ENDPOINT (e.g., https://myproj.eastus2.inference.ai.azure.com)
 - AZURE_AI_FOUNDRY_PROJECT  (project name)
 - AZURE_AI_FOUNDRY_AGENT_ID (agent GUID or name)

For authentication, uses Azure service principal credentials:
 - AZURE_TENANT_ID (tenant ID)
 - AZURE_CLIENT_ID (client/app ID)  
 - AZURE_CLIENT_SECRET (client secret)

Falls back to DefaultAzureCredential if service principal credentials are not available.
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
        from azure.identity import DefaultAzureCredential, ClientSecretCredential
        from azure.ai.projects import AIProjectClient
    except Exception as ex:
        raise ImportError(
            "azure-ai-projects (and azure-identity) is required to use Azure Agent Service. "
            "Install it via 'pip install azure-ai-projects azure-identity'."
        ) from ex

    # Use Azure service principal credentials for authentication
    # These should be set in the container environment
    tenant_id = os.getenv('AZURE_TENANT_ID')
    client_id = os.getenv('AZURE_CLIENT_ID')
    client_secret = os.getenv('AZURE_CLIENT_SECRET')
    
    if tenant_id and client_id and client_secret:
        # Use service principal credentials
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret
        )
    else:
        # Fall back to default credential chain
        credential = DefaultAzureCredential()
    
    # The endpoint should include the full project path
    full_endpoint = f"{endpoint}/api/projects/{project_name}"
    client = AIProjectClient(endpoint=full_endpoint, credential=credential)

    # Create thread
    thread = client.agents.threads.create()
    
    # Add messages to the thread
    for msg in messages:
        client.agents.messages.create(
            thread_id=thread.id,
            role=msg["role"],
            content=msg["content"]
        )

    # Create and process the run
    run = client.agents.runs.create_and_process(
        thread_id=thread.id,
        agent_id=agent_name_or_id
    )

    # Check if the run was successful
    if run.status == "failed":
        raise Exception(f"Agent run failed: {run.last_error}")
    
    # Get the messages from the thread
    from azure.ai.agents.models import ListSortOrder
    thread_messages = client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING)

    # Try to extract the assistant message from the response
    assistant_text = None
    try:
        # Find the last assistant message
        for message in thread_messages:
            if message.role == "assistant" and message.text_messages:
                assistant_text = message.text_messages[-1].text.value
        
        if not assistant_text:
            assistant_text = "No assistant response found in thread"
            
    except Exception as ex:
        assistant_text = f"Error extracting response: {str(ex)}"

    if not assistant_text:
        assistant_text = f"Agent run completed with status: {getattr(run, 'status', 'unknown')}"

    return assistant_text, run
