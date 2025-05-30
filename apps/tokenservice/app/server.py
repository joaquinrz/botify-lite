import logging
import os
import time
import threading
import toml
import _additional_version_info
import requests
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse



from app import (
    allowed_origins,
    url_prefix,
    log_level,
    local_mode,
    speech_region,
    speech_key
)

if  local_mode:
    from app import (
        speech_region,
        speech_key
    )
else:
    from azure.identity import DefaultAzureCredential
    from app import (
    api_scope,
    speech_service_scope,
    speech_endpoint,
    speech_resource_id
    )

# Set root logger level before other imports
logging.getLogger().setLevel(log_level)
logger = logging.getLogger(__name__)

# Load the pyproject.toml file
pyproject = toml.load("pyproject.toml")

# Extract the version, short_sha, and build_timestamp
version = pyproject.get("tool", {}).get("poetry", {}).get("version", "Version not found")

if  _additional_version_info.__short_sha__ and _additional_version_info.__build_timestamp__:
    version = version + "-" + _additional_version_info.__short_sha__ + "-" + _additional_version_info.__build_timestamp__

app = FastAPI(
    root_path=url_prefix,
    title="Botify Lite Token Service",
    version=version,
    description="A token service for public clients to obtain access tokens for the Botify Lite API and Speech Service."
)

# Set all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Get the app version
@app.get("/version")
def get_version():
    return {"version": app.version}

# Global variables
speech_token = None # Speech token

def get_sas_token():

        url = f"https://{speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {
            "Content-type": "application/x-www-form-urlencoded",
            "Content-length": "0",
            "Ocp-Apim-Subscription-Key": speech_key,
        }

        response = requests.post(url, headers=headers)
        response.raise_for_status()

        logging.info(f"Response status code: {response.status_code}")

        return response.text

# Refresh the speech token every 9 minutes
def refreshSpeechToken() -> None:
    global speech_token
    while True:
        try:
            if local_mode:
                speech_token = get_sas_token()
            else:
                credential = DefaultAzureCredential()
                token = credential.get_token(speech_service_scope)
                speech_token = f'aad#{speech_resource_id}#{token.token}'
        except:
            logger.error("Failed to refresh speech token")
        finally:
            logger.info("Sleeping for 9 minutes...")
            time.sleep(60 * 9)

# Default route -> leads to the OpenAPI Swagger definition
@app.get("/", include_in_schema=False)
async def redirect_root_to_docs():
    return RedirectResponse(f'{url_prefix}/docs')

@app.post("/speech")
def get_speech_token(response: Response):
    if speech_token is None:
        raise HTTPException(status_code=500, detail="Failed to get speech token")
    if 'speech_endpoint' in globals() and speech_endpoint:
        response.headers['SpeechEndpoint'] = speech_endpoint
    return {"speech_token":speech_token}

@app.post("/api")
def get_api_token():
    try:
        credential = DefaultAzureCredential()
        token = credential.get_token(api_scope)
    except:
        raise HTTPException(status_code=500, detail="Failed to get API token")
    return {"access_token": token.token, "expires_on": token.expires_on}

# Start the speech token refresh thread
speechTokenRefereshThread = threading.Thread(target=refreshSpeechToken)
speechTokenRefereshThread.daemon = True
logger.debug(f"Starting speech token refresh thread")
speechTokenRefereshThread.start()
