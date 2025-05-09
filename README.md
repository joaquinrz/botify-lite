# Botify Lite Assistant API Application

A complete solution for interacting with Azure OpenAI, consisting of a FastAPI backend server and a CLI chat client application.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fjoaquinrz%2Fbotify-lite%2Fmain%2Fazuredeploy.json)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/joaquinrz/botify-lite)

## Project Structure

- `apps/`: Contains all application components
  - `botify_server/`: Botify Assistant Server (FastAPI backend)
  - `botify_cli/`: Botify CLI client
  - `tokenservice/`: Token Service for secure Azure token management
  - `react-frontend/`: React web frontend for browser-based interaction
  - `credentials.env`: Environment variables configuration file
  - `credentials.env.template`: Template file for environment variables
  - `otel_col/`: OpenTelemetry Collector configuration and Dockerfile
- `data/`: JSON files for vector store knowledge base
- `docker-compose.yml`: Docker Compose configuration for running all services
- `scripts/`: Utility scripts for setup and maintenance

## Features

- **Botify Assistant Server**:
  - Interfaces with Azure OpenAI API
  - Supports both streaming and non-streaming responses
  - RESTful API endpoints
  - Complete with unit tests
  - Azure Content Safety integration for content moderation
  - Vector store integration for enhanced knowledge retrieval
  - Optional token-based authentication

- **Botify CLI Client**:
  - Interactive terminal interface using Rich
  
- **Token Service**:
  - Secure token acquisition for Azure resources
  - Support for API access tokens and Speech Service tokens
  - Automatic token refresh
  - Works with both managed identities and service principals
  
- **React Frontend**:
  - Modern web interface for browser-based chat
  - Azure Speech Services integration for voice input/output
  - Streaming responses for real-time interaction
  - Secure token authentication with the backend API
  - Support for both streaming and non-streaming modes
  - Chat history management
  - Command system for various operations

- **Observability & Telemetry**:
  - Comprehensive telemetry through OpenTelemetry and Traceloop SDK
  - Local observability stack with Aspire Dashboard

- **Privacy & Security**:
  - Content moderation via Azure Content Safety
  - Configurable telemetry with privacy controls
  - Sensitive information redaction in logs and traces

## Requirements

- Python 3.9 or higher
- Poetry for dependency management
- Docker and Docker Compose (optional, for containerized deployment)
- Azure OpenAI service setup with proper credentials

## Development Environments

### GitHub Codespaces / Dev Containers

This repository is configured with Dev Containers, allowing you to develop in a consistent environment either through GitHub Codespaces or locally using VS Code with the Dev Containers extension.

#### Using GitHub Codespaces (Cloud-based)

1. Click the "Open in GitHub Codespaces" button at the top of this README
2. GitHub will create and launch a Codespace with all dependencies pre-installed
3. Wait for the container to finish building (this may take a few minutes on first launch)
4. Once loaded, the development environment will include:
   - Python 3.13 and Poetry for dependency management
   - Pre-configured VS Code extensions for Python development
   - Zsh with helpful plugins and git customizations
   - Azure CLI and Docker-in-Docker support

#### Using Dev Containers Locally

1. Prerequisites:
   - Visual Studio Code with the [Dev Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers)
   - Docker Desktop installed and running

2. Open the repository in VS Code:

   ```bash
   git clone https://github.com/joaquinrz/botify-lite.git
   cd botify-lite
   code .
   ```

3. When prompted, click "Reopen in Container", or:
   - Press F1 and select "Dev Containers: Reopen in Container"

The container will build with the same configuration as GitHub Codespaces.

## Getting Started

### 1. Deploy to Azure

1. Click the "Deploy to Azure" button at the top of this README to start the deployment process.
2. Complete the Azure deployment form with your preferred settings.
3. After the deployment completes, check the outputs section of the deployment for:
   - `openAIServiceEndpoint`: The endpoint URL for your Azure OpenAI service
   - `contentSafetyServiceEndpoint`: The endpoint URL for your Azure Content Safety service
   - `contentSafetyServiceName`: The name of your Azure Content Safety service

### 2. Get Your API Key

1. Navigate to your newly deployed Azure OpenAI resource in the Azure portal
2. Go to "Keys and Endpoint" in the left menu
3. Copy one of the available keys (either KEY 1 or KEY 2)

### 3. Configure Environment Variables

1. Create your environment file by copying the template:

   ```bash
   cp apps/credentials.env.template apps/credentials.env
   ```

2. Update your `apps/credentials.env` file with the information from your deployment:

   ```bash
   # Azure OpenAI Settings
   AZURE_OPENAI_ENDPOINT=your_openAIServiceEndpoint_from_deployment_output
   AZURE_OPENAI_API_KEY=your_api_key_from_azure_portal
   AZURE_OPENAI_API_VERSION=2024-05-01-preview
   AZURE_OPENAI_MODEL_NAME=gpt-4o-mini

   # Azure Content Safety Settings
   AZURE_CONTENT_SAFETY_ENDPOINT=your_contentSafetyServiceEndpoint_from_deployment_output
   AZURE_CONTENT_SAFETY_KEY=your_content_safety_key_from_azure_portal
   
   # Server Settings (for backend)
   SERVER_HOST=0.0.0.0
   SERVER_PORT=8000

   # Telemetry Settings
   TELEMETRY_ENABLED=false
   OTEL_EXPORTER_OTLP_ENDPOINT=http://otelcol:4317
   AZURE_APPINSIGHTS_CONNECTION_STRING=your_app_insights_connection_string

   # Client Settings (for CLI)
   API_BASE_URL=http://localhost:8000
   USE_STREAMING=true
   CHAT_HISTORY_FILE=./chat_history.txt
   ```

Replace:

- `your_openAIServiceEndpoint_from_deployment_output` with the OpenAI endpoint URL from the deployment outputs
- `your_api_key_from_azure_portal` with the OpenAI API key from the Azure portal
- `your_contentSafetyServiceEndpoint_from_deployment_output` with the Content Safety endpoint from the deployment outputs
- `your_contentSafetyServiceName_from_deployment_output` with the Content Safety service name from the deployment outputs
- `your_content_safety_key_from_azure_portal` with the Content Safety API key from the Azure portal

The model name should already be correctly set to "gpt-4o-mini" as specified in the deployment template.

Without valid credentials, the application will display connection errors when attempting to interact with the AI service.

### 4. Create and Configure Vector Store

The application uses an Azure OpenAI vector store to provide information to the assistant. Follow these steps to create and configure your vector store:

1. Make sure you have configured your environment variables in the previous step

2. Run the vector store creation script:

   ```bash
   # Install dependencies
   poetry install

   # Run the script with Poetry
   poetry run python scripts/create_vector_store.py
   ```

3. The script will:
   - Locate all JSON files in the `data/` directory
   - Create a new vector store in your Azure OpenAI service
   - Upload all JSON files to the vector store
   - Display the vector store ID when complete

4. Copy the vector store ID from the script output and add it to your `apps/credentials.env` file:

   ```bash
   # Add this line to your credentials.env file
   AZURE_OPENAI_VECTOR_STORE_ID=your_vector_store_id
   ```

This step is essential for the assistant to access knowledge from the vector store.

### 5. Running the Applications using Poetry

#### Prepare the Poetry virtual environment

```bash
# Install dependencies
poetry install

# Load environment variables
export $(grep -v '^#' apps/credentials.env | xargs) 2>/dev/null || true
```

#### Run the Server Application

```bash
# Navigate to the server directory
cd apps/botify_server

# Install dependencies
poetry install

# Start the server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

#### Run the CLI Application in a new terminal

```bash
# Navigate to the CLI directory
cd apps/botify_cli

# Install dependencies
poetry install

# Start the CLI
poetry run python -m app.main
```

### 6. Running the Applications using Docker

For a containerized setup using Docker Compose:

```bash
# Build and start the containers
docker-compose up --build

# To run in detached mode
docker-compose up -d

# Access the CLI client in a running container
docker exec -it botify_cli python -m app.main
```

## Using the CLI Chat Client

The CLI client provides an interactive terminal interface for chatting with the Azure OpenAI service.

### Commands

- Type your message and press Enter to chat with the AI
- `/history`: View your recent chat history
- `/clear`: Clear chat history
- `/stream on` or `/stream off`: Toggle streaming mode
- `/exit` or `/quit`: Exit the application

## Telemetry and Observability

Botify Lite includes a comprehensive observability stack:

### Components

- **Traceloop SDK**: Automatically instruments OpenAI API calls, FastAPI routes, and more
- **OpenTelemetry Collector**: Collects and processes telemetry data
- **Aspire Dashboard**: Visual interface for exploring traces and metrics

### Dashboard Access

When running with Docker Compose, access the Aspire Dashboard at:
- http://localhost:18888

This provides visibility into:
- API request/response flows
- LLM prompt tokens and completion tokens
- Request latency and errors
- Dependencies between services


## Common Errors and Solutions

### Missing or Invalid Azure OpenAI Credentials

If you see errors like `[Errno -2] Name or service not known` or `openai.APIConnectionError: Connection error`, this typically means that:

1. Your Azure OpenAI endpoint URL is incorrect or empty
2. Your API key is missing or invalid
3. The specified model name doesn't exist in your Azure OpenAI resource

Solution: Check and update your credentials in the `apps/credentials.env` file with valid values from your Azure OpenAI service.

### Telemetry Connection Issues

If services can't connect to the telemetry system:

1. Ensure the OpenTelemetry Collector is running (`docker ps` should show the `otelcol` container)
2. Check that `OTEL_EXPORTER_OTLP_ENDPOINT` is set correctly in your environment
3. Verify network connectivity between containers (they should all be on the `botify_net` network)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
