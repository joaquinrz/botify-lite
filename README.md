# Botify Lite Assistant API Application

A complete solution for interacting with Azure OpenAI, consisting of a FastAPI backend server, a web-based React frontend, and a CLI chat client application.

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
  - **Dual Content Safety Strategies**: Azure Content Safety and NeMo Guardrails with runtime switching
  - Vector store integration for enhanced knowledge retrieval
  - Optional token-based authentication

- **Botify CLI Client**:
  - Interactive terminal interface using Rich
  
- **Token Service**:
  - Secure token acquisition for Azure resources
  - Support for API access tokens and Azure Speech Service tokens
  - Automatic token refresh with configurable expiration
  - Works with both managed identities and service principals
  - Lightweight REST API for client token requests
  
- **React Frontend**:
  - Modern, responsive web interface for browser-based chat
  - Azure Speech Services integration for voice input/output
  - Text-to-speech and speech-to-text capabilities
  - Streaming responses for real-time interaction
  - Secure token authentication with the backend API
  - Support for both streaming and non-streaming modes
  - Persistent chat history management
  - Command system for various operations

- **Observability & Telemetry**:
  - Comprehensive telemetry through OpenTelemetry and Traceloop SDK
  - Local observability stack with Aspire Dashboard

- **Privacy & Security**:
  - **Content moderation with dual strategies**: Azure Content Safety and NeMo Guardrails
  - **Runtime strategy switching** via environment variables
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
   - `contentSafetyServiceName`: The name of your Azure Content Safety service

### 2. Get Your API Keys

1. Navigate to your newly deployed Azure OpenAI resource in the Azure portal
2. Go to "Keys and Endpoint" in the left menu
3. Copy one of the available keys (either KEY 1 or KEY 2)
4. Repeat the process for the Content Safety service if you plan to use content moderation

### 3. Configure Environment Variables

1. Create your environment file by copying the template:

   ```bash
   cp apps/credentials.env.template apps/credentials.env
   ```

2. Update your `apps/credentials.env` file with the information from your deployment:

   ```bash
   # Azure OpenAI Configuration
   AZURE_OPENAI_ENDPOINT=your_openAIServiceEndpoint_from_deployment_output
   AZURE_OPENAI_API_KEY=your_api_key_from_azure_portal
   AZURE_OPENAI_API_VERSION=2024-07-01
   AZURE_OPENAI_DEPLOYMENT=gpt-4o-mini
   
   # Azure Content Safety (Optional but recommended)
   AZURE_CONTENT_SAFETY_ENDPOINT=your_contentSafetyServiceEndpoint_from_deployment_output
   AZURE_CONTENT_SAFETY_KEY=your_content_safety_key_from_azure_portal
   
   # Azure Speech Service (Optional, for voice capabilities)
   AZURE_SPEECH_KEY=your_speech_service_key
   AZURE_SPEECH_REGION=eastus
   
   # Vector Store Settings (Optional, for knowledge base)

  # Telemetry Settings
   TELEMETRY_ENABLED=false
   OTEL_EXPORTER_OTLP_ENDPOINT=http://otelcol:4317
   AZURE_APPINSIGHTS_CONNECTION_STRING=your_app_insights_connection_string
   AZURE_OPENAI_VECTOR_STORE_ID=your_vector_store_id
   ```

Replace the placeholder values with your actual Azure service details.

### 4. Create and Configure Vector Store (Optional)

To use knowledge retrieval features, create a vector store from the provided JSON files:

```bash
# Install dependencies
poetry install

# Run the vector store creation script
poetry run create-vector-store
```

The script will create a vector store and display its ID, which should be added to your `apps/credentials.env` file.

### 5. Content Safety Strategy Configuration

The application supports two content safety strategies that can be switched at runtime:

#### Azure Content Safety (Default)
- Uses Azure AI Content Safety service for content moderation
- Requires Azure Content Safety service credentials in your environment
- Set `CONTENT_SAFETY_STRATEGY=AZURE` in your credentials.env file (or leave unset as this is the default)

#### NeMo Guardrails
- Uses NVIDIA's NeMo Guardrails for content safety
- No additional API credentials required
- Set `CONTENT_SAFETY_STRATEGY=NEMO` in your credentials.env file

To configure your preferred strategy, add this line to your `apps/credentials.env` file:

```bash
# Content Safety Strategy (AZURE or NEMO)
CONTENT_SAFETY_STRATEGY=AZURE  # Default, can be changed to NEMO
```

**Testing Both Strategies:**
Use the simple comparison script to test both strategies automatically:

```bash
# This will switch strategies, restart the server, run tests, and compare results
python simple_strategy_test.py
```

The script will:
1. Set Azure strategy in credentials.env and restart the server
2. Run content safety tests
3. Set NeMo strategy in credentials.env and restart the server
4. Run content safety tests again
5. Compare and display the results

### 6. Running the Application

You can run the application using Docker Compose, which will start all services:

```bash
docker compose up
```

Or run individual components:

```bash
# Run just the backend server
docker-compose up botify_server

# Run the CLI client
docker-compose up botify_cli

# Run the web frontend and its dependencies
docker-compose up react-frontend botify_server tokenservice
```

### 7. Accessing the Web Interface

Once the application is running, you can access:

- Web Interface: [http://localhost:5173](http://localhost:5173)
- API Backend: [http://localhost:8000/docs](http://localhost:8000/docs)
- Token Service: [http://localhost:8081/docs](http://localhost:8081/docs)

### 7. Using the CLI Client

The CLI client provides an interactive terminal interface:

```bash
# Using poetry
poetry run python -m botify_cli.app.main

# Using Docker
docker-compose run botify_cli
```

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
