# Azure AI Foundry Agent Service Integration

## Overview

SimpleChat supports integration with Azure AI Foundry Agent Service, allowing you to leverage pre-built, managed AI agents hosted in Azure AI Foundry. This integration provides a streamlined way to use sophisticated AI agents without managing the underlying infrastructure.

## What is Azure AI Foundry Agent Service?

Azure AI Foundry Agent Service is a managed service that allows you to:
- Create and deploy AI agents with custom instructions and capabilities
- Access agents through a simple REST API
- Leverage Azure's enterprise-grade security and scalability
- Use pre-built templates or create custom agents tailored to your needs

## Benefits of Using Agent Service

1. **Managed Infrastructure**: No need to manage AI model deployments or scaling
2. **Enterprise Security**: Built-in Azure security, compliance, and governance
3. **Cost Efficiency**: Pay only for what you use with managed scaling
4. **Rapid Deployment**: Quick setup without complex model configuration
5. **Advanced Capabilities**: Access to latest AI capabilities and tools

## Prerequisites

Before configuring the Agent Service integration, ensure you have:

1. **Azure Subscription** with appropriate permissions
2. **Azure AI Foundry Project** created and configured
3. **Service Principal** with access to your AI Foundry project
4. **Agent Created** in Azure AI Foundry with a valid Agent ID

## Configuration

### Step 1: Enable Agent Service in Admin Settings

1. Navigate to **Admin Settings** in SimpleChat
2. Scroll to the **Azure Agent Service** section
3. Enable the **"Enable Azure Agent Service"** toggle
4. Choose your configuration method:
   - **Use Environment Variables** (recommended for production)
   - **Manual Configuration** (for testing or specific setups)

### Step 2: Environment Variables Configuration

If using environment variables, add these to your `.env.local` file:

```bash
# Azure AI Foundry Agent Service
AZURE_AI_FOUNDRY_ENDPOINT=https://your-project.services.ai.azure.com/
AZURE_AI_FOUNDRY_PROJECT=your-project-name
AZURE_AI_FOUNDRY_AGENT_ID=your-agent-id

# Azure Service Principal for authentication
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

### Step 3: Manual Configuration (Alternative)

If not using environment variables:

1. In Admin Settings, disable **"Use environment variables"**
2. Fill in the following fields:
   - **Endpoint**: Your AI Foundry project endpoint
   - **Project Name**: Your AI Foundry project name
   - **Agent ID**: The ID of your created agent

## Finding Your Configuration Values

### Azure AI Foundry Endpoint
1. Go to [Azure AI Foundry](https://ai.azure.com)
2. Navigate to your project
3. In the project overview, find the **"Endpoint"** value
4. Format: `https://your-project.services.ai.azure.com/`

### Project Name
1. In Azure AI Foundry, your project name is displayed in the project overview
2. This is the same name you used when creating the project

### Agent ID
1. In your Azure AI Foundry project, go to **"Agents"**
2. Select your agent
3. The Agent ID is displayed in the agent details (format: `asst_xxxxxxxxxx`)

### Service Principal Configuration
1. In Azure Portal, go to **Azure Active Directory** > **App Registrations**
2. Create or select an existing app registration
3. Note the **Application (client) ID** and **Directory (tenant) ID**
4. Create a **Client Secret** in the "Certificates & secrets" section
5. Ensure the service principal has appropriate permissions to your AI Foundry project

## How It Works

When Azure Agent Service is enabled:

1. **Model Selection**: The model dropdown shows "Agent Service" instead of individual models
2. **Request Routing**: All chat requests are routed to your Azure AI Foundry agent
3. **Authentication**: Uses service principal credentials for secure access
4. **Response Handling**: Agent responses are processed and displayed normally

## User Experience

### For End Users
- When Agent Service is active, users will see **"Agent Service"** in the model dropdown
- Chat functionality remains the same - users type messages and receive responses
- The underlying agent handles the conversation using its configured instructions and capabilities

### For Administrators
- Toggle Agent Service on/off from admin settings
- Configure endpoint and authentication details
- Monitor usage through Azure AI Foundry portal

## Troubleshooting

### Common Issues

**Agent Service not working:**
- Verify all environment variables are set correctly
- Check that the service principal has permissions to the AI Foundry project
- Ensure the Agent ID is correct and the agent is deployed

**Authentication errors:**
- Verify tenant ID, client ID, and client secret are correct
- Check that the service principal exists and is properly configured
- Ensure the service principal has "Cognitive Services User" role or equivalent

**Endpoint connectivity issues:**
- Verify the endpoint URL is correct and accessible
- Check network connectivity and firewall settings
- Ensure the project name matches exactly (case-sensitive)

### Debug Mode

Enable debug logging by checking container logs:
```bash
docker logs <container-name> --tail 50
```

Look for debug messages starting with "DEBUG: enable_azure_agent_service" to verify configuration.

## Best Practices

1. **Security**:
   - Use environment variables for production deployments
   - Rotate client secrets regularly
   - Use managed identity when possible (future enhancement)

2. **Monitoring**:
   - Monitor agent usage in Azure AI Foundry portal
   - Set up alerts for usage thresholds
   - Review agent conversations for quality

3. **Cost Management**:
   - Monitor token usage and costs
   - Implement usage quotas if needed
   - Consider agent caching strategies

## Limitations

- Currently supports one agent per SimpleChat instance
- Requires service principal authentication (managed identity support planned)
- Agent configuration must be done in Azure AI Foundry portal

## Future Enhancements

- Support for multiple agents per instance
- Managed identity authentication
- Agent selection per user or conversation
- Advanced agent configuration within SimpleChat UI

## Support

For issues related to:
- **SimpleChat Integration**: Check container logs and configuration
- **Azure AI Foundry**: Refer to [Azure AI Foundry documentation](https://docs.microsoft.com/azure/ai-services/ai-foundry/)
- **Service Principal Setup**: Refer to [Azure AD documentation](https://docs.microsoft.com/azure/active-directory/develop/howto-create-service-principal-portal)
