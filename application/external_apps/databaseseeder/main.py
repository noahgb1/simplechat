import os
import requests
from msal import ConfidentialClientApplication
import logging
from dotenv import load_dotenv

#############################################
# --- Configuration ---
#############################################
load_dotenv()

# From environment variables .env file for security
AUTHORITY_URL = os.getenv("AUTHORITY_URL")
TENANT_ID = os.getenv("AZURE_TENANT_ID")  # Directory (tenant) ID
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")  # Application (client) ID for your client app
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")  # Client secret for your client app (use certificates in production)
API_SCOPE = os.getenv("API_SCOPE") # Or a specific scope defined for your API, e.g., "api://<your-api-client-id>/.default" for application permissions
API_BASE_URL = os.getenv("API_BASE_URL") # Base URL for your API
API_ENDPOINT_URL = f"{API_BASE_URL}/api/groups/discover?showAll=true", API_BASE_URL # Your custom API endpoint for document upload
USER_ID = os.getenv("USER_ID")  # User ID for whom the groups are being fetched
g_ACCESS_TOKEN = None  # Placeholder for the access token function

# Configure logging for better debugging
logname = "./logfile.log"
# logging.basicConfig(filename=logname,
#     filemode='a',
#     format='%(asctime)s,%(msecs)03d %(name)s %(levelname)s %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     level=logging.DEBUG)
logging.basicConfig(level = logging.DEBUG) # DEBUG, INFO, WARNING, ERROR, and CRITICAL
logger = logging.getLogger(__name__)

#############################################
# --- Function Library ---
#############################################
def get_access_token():
    """
    Acquires an access token from Microsoft Entra ID using the client credentials flow.
    """
    authority = f"{AUTHORITY_URL}/{TENANT_ID}"
    app = ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=authority
    )

    try:
        # Acquire a token silently from cache if available
        result = app.acquire_token_silent(scopes=[API_SCOPE], account=None)
        if not result:
            # If no token in cache, acquire a new one using client credentials flow
            logger.info("No token in cache, acquiring new token using client credentials flow.")
            result = app.acquire_token_for_client(scopes=[API_SCOPE])

        if "access_token" in result:
            logger.info("Successfully acquired access token.")
            return result["access_token"]
        else:
            logger.error(f"Error acquiring token: {result.get('error')}")
            logger.error(f"Description: {result.get('error_description')}")
            logger.error(f"Correlation ID: {result.get('correlation_id')}")
            return None
    except Exception as e:
        logger.error(f"An unexpected error occurred during token acquisition: {e}")
        return None

def groups_get(user_id, access_token):
    logger.debug(f"groups_get: {user_id}")
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    data = {
        'userId': user_id
    }

    try:
        logger.debug(f"API Endpoint: {API_ENDPOINT_URL}")
        response = requests.post(API_ENDPOINT_URL, headers=headers, data=data, timeout=60)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)

        logger.debug(f"Response: {response.text}")

    except requests.exceptions.HTTPError as e:
        logger.error(f"Response content: {e.response.text}")
        return False
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Response content: {e.response.text}")
        return False
    except requests.exceptions.Timeout as e:
        logger.error(f"Response content: {e.response.text}")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Response content: {e.response.text}")
        return False
    except Exception as e:
        logger.error(f"Response content: {e.response.text}")
        return False

def main():
    """
    Main function to iterate through files and upload them.
    """
    logger.warning("Database seeder starting...")
    g_ACCESS_TOKEN = get_access_token()
    if not g_ACCESS_TOKEN:
        logger.critical("Failed to obtain access token. Aborting document upload.")
        return

    logger.warning("Getting Groups from CosmosDb...")
    groups_get(USER_ID, access_token=g_ACCESS_TOKEN)

    logger.warning("Database seeder complete...")

if __name__ == "__main__":
    main()