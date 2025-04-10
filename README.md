# Botify Lite Assistant API Application

A complete solution for interacting with Azure OpenAI, consisting of a FastAPI backend server and a CLI chat client application.

[![Deploy to Azure](https://aka.ms/deploytoazurebutton)](https://portal.azure.com/#create/Microsoft.Template/uri/https%3A%2F%2Fraw.githubusercontent.com%2Fjoaquinrz%2Fbotify-lite%2Fmain%2Fazuredeploy.json)

## Project Structure

- `apps/`: Contains all application components
  - `botify_server/`: Botify Assistant Server (FastAPI backend)
  - `botify_cli/`: Botify CLI client
  - `credentials.env`: Environment variables configuration file
  - `credentials.env.template`: Template file for environment variables
- `docker-compose.yml`: Docker Compose configuration for running both applications

## Features

- **Botify Assistant Server**:
  - Interfaces with Azure OpenAI API
  - Supports both streaming and non-streaming responses
  - RESTful API endpoints
  - Complete with unit tests

- **Botify CLI Client**:
  - Interactive terminal interface using Rich
  - Support for both streaming and non-streaming modes
  - Chat history management
  - Command system for various operations

## Requirements

- Python 3.9 or higher
- Poetry for dependency management
- Docker and Docker Compose (optional, for containerized deployment)
- Azure OpenAI service setup with proper credentials

## Getting Started

### 1. Deploy to Azure

1. Click the "Deploy to Azure" button at the top of this README to start the deployment process.
2. Complete the Azure deployment form with your preferred settings.
3. After the deployment completes, check the outputs section of the deployment for:
   - `openAIServiceEndpoint`: The endpoint URL for your Azure OpenAI service

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
   
   # Server Settings (for backend)
   SERVER_HOST=0.0.0.0
   SERVER_PORT=8000
   
   # Client Settings (for CLI)
   API_BASE_URL=http://localhost:8000
   USE_STREAMING=true
   CHAT_HISTORY_FILE=./chat_history.txt
   ```

Replace:
- `your_openAIServiceEndpoint_from_deployment_output` with the endpoint URL from the deployment outputs
- `your_api_key_from_azure_portal` with the API key you copied from the Azure portal

The model name should already be correctly set to "gpt-4o-mini" as specified in the deployment template.

Without valid credentials, the application will display connection errors when attempting to interact with the AI service.

### 4. Create and Configure Vector Store

The application uses an Azure OpenAI vector store to provide information to the assistant. Follow these steps to create and configure your vector store:

1. Make sure you have configured your environment variables in the previous step

2. Run the vector store creation script:
   ```bash
   
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

### 5. Local Development Setup

If you want to run the applications locally for development:

#### Backend Setup

```bash
# Navigate to backend directory
cd apps/botify_server

# Install dependencies
poetry install

# Run the backend server
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### CLI Client Setup

```bash
# Navigate to CLI directory
cd apps/botify_cli

# Install dependencies
poetry install

# Run the CLI client
poetry run python -m app.main
```

### 5. Docker Setup

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

### Command-line Options

The CLI client accepts the following command-line options:

```bash
# Run with a custom server URL
python -m app.main --server http://custom-server:8000

# Explicitly enable or disable streaming
python -m app.main --stream  # Enable streaming
python -m app.main --no-stream  # Disable streaming

# Specify a custom history file location
python -m app.main --history ./custom_history.txt
```

## Running Tests

### Backend Tests

```bash
cd apps/botify_server
poetry run pytest
```

### CLI Tests

```bash
cd apps/botify_cli
poetry run pytest
```

## API Endpoints

The backend API exposes the following endpoints:

- `GET /`: Root endpoint (health check)
- `GET /health`: Health check endpoint
- `POST /api/chat`: Non-streaming chat endpoint
- `POST /api/chat/stream`: Streaming chat endpoint using Server-Sent Events (SSE)

## Architecture

This project follows a client-server architecture:

1. The **Botify Assistant Server** (FastAPI backend):
   - Manages communication with Azure OpenAI
   - Handles both streaming and non-streaming requests
   - Provides a RESTful API for clients to consume

2. The **Botify CLI Client**:
   - Provides a user-friendly terminal interface
   - Communicates with the backend server via HTTP
   - Manages local chat history
   - Supports both streaming and non-streaming modes

## Troubleshooting

- **Connection issues**: Ensure the backend server is running and accessible from the CLI client
- **Authentication errors**: Verify your Azure OpenAI credentials in the `apps/credentials.env` file
- **Docker networking problems**: Make sure Docker containers can communicate with each other
- **Missing credentials error**: If you see connection errors when running the application, make sure you have properly filled out the `apps/credentials.env` file with valid Azure OpenAI credentials.

## Common Errors and Solutions

### Missing or Invalid Azure OpenAI Credentials
If you see errors like `[Errno -2] Name or service not known` or `openai.APIConnectionError: Connection error`, this typically means that:
1. Your Azure OpenAI endpoint URL is incorrect or empty
2. Your API key is missing or invalid
3. The specified model name doesn't exist in your Azure OpenAI resource

Solution: Check and update your credentials in the `apps/credentials.env` file with valid values from your Azure OpenAI service.

## License

This project is licensed under the MIT License - see the LICENSE file for details.