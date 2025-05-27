# ReadMe

## Manual Pre-Requisites (Critically Important)

Create Entra ID App Registration:

Go to Azure portal > Microsoft Entra ID > App registrations > New registration.

- Provide a name (e.g., $appRegistrationName from the script's logic).
- Supported account types: Usually "Accounts in this organizational directory only."
- Do not configure Redirect URI yet. You will get these from the Bicep output.
- Once created, note down the Application (client) ID (this is appRegistrationClientId parameter).
- Go to "Certificates & secrets" > "New client secret" > Create a secret and copy its Value immediately (this is appRegistrationClientSecret parameter).
- **** NO **** Go to "Token configuration" and enable "ID tokens" and "Access tokens" for implicit grant and hybrid flows if needed by your app (the script attempts az ad app update --enable-id-token-issuance true --enable-access-token-issuance true).
- The script also adds API permissions (User.Read, profile, email to Microsoft Graph) and attempts to add owners. These should be configured manually on the App Registration.
- The script also references appRegistrationRoles.json. If your application defines app roles, configure these in the App Registration manifest.
- Obtain the Object ID of the Service Principal associated with this App Registration: az ad sp show --id <Your-App-Registration-Client-ID> --query id -o tsv. This will be the appRegistrationSpObjectId parameter.

Create Entra ID Security Groups: If your application relies on the security groups ($global_EntraSecurityGroupNames), create them manually in Entra ID.

Azure Container Registry (ACR): Ensure the ACR specified by acrName exists and the image imageName is pushed to it.

Azure OpenAI Access: If useExistingOpenAiInstance is true, ensure the specified existing OpenAI resource exists and you have its name and resource group. If false, ensure your subscription is approved for Azure OpenAI and the chosen SKU and region support it.

## Deploy

Create a resource group if you don't have one: az group create --name MySimpleChatRG --location usgovvirginia
Deploy the Bicep file:

### azure cli

#### validate before deploy

az bicep build --file main.bicep

az deployment group validate `
--resource-group MySimpleChatRG `
--template-file main.bicep `
--parameters main.json

az deployment group create `
--resource-group MySimpleChatRG `
--template-file main.bicep `
--parameters main.bicepparam `
--parameters appRegistrationClientSecret="YOUR_APP_REG_SECRET_VALUE"

## Post-Deployment Manual Steps (from Bicep outputs and script)

### App Registration

- Redirect URIs: Take appRegistrationRedirectUri1, appRegistrationRedirectUri2, and appRegistrationLogoutUrl from the Bicep deployment output and add them to your Entra App Registration under "Authentication" > "Web" > "Redirect URIs" and "Front-channel logout URL".

- API Permissions Grant Consent: In the App Registration > "API permissions", grant admin consent for the configured permissions if not already done.

- Create all appRoles per documentation.

### Entra Security Groups

- Assignments: If you created security groups, assign them to the corresponding Enterprise Application application roles and add members to the security groups.

### App Service

- Authentication
  - The script has comments about az webapp auth update and az webapp auth microsoft update. The Bicep file includes a basic authsettingsV2 block. You may need to refine this or use az cli commands post-deployment for a more advanced auth setup as hinted in the script, especially if the simple Bicep auth settings are not sufficient.

- Restart & Test: Restart the App Service and test the Web UI.

### Azure AI Search

- Manually create 2 Indexes: Deploy your search index schemas (ai_search-index-group.json, ai_search-index-user.json) using Index as Json in the Azure portal.

### Admin center in Web UI application

- Navigate to the Web UI > Admin and configure the settings.
