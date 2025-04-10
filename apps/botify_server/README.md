# Botify Server

FastAPI server for Botify Assistant interactions with Azure OpenAI.

## Overview

Botify Server is the backend component of the Botify Lite Assistant API Application. It provides a robust interface between clients and Azure OpenAI services, handling authentication, request processing, and response streaming in a reliable and efficient manner.

## Features

- **Azure OpenAI Integration**: Seamless connection to Azure OpenAI services
- **Dual Response Modes**: Support for both streaming and non-streaming API responses
- **RESTful API Design**: Clean, well-structured API endpoints
- **Vector Store Support**: Integration with Azure OpenAI vector store for enhanced responses
- **Comprehensive Testing**: Complete test coverage for all core functionality
- **Docker Support**: Containerization for easy deployment

## API Endpoints

The server exposes the following endpoints:

### Health Checks

- `GET /`: Root endpoint providing basic server information
- `GET /health`: Health check endpoint for monitoring server status

### Chat Endpoints

- `POST /api/chat`: Non-streaming chat endpoint
  - Accepts chat history and returns complete responses
  - Suitable for applications that need the full response at once

- `POST /api/chat/stream`: Streaming chat endpoint using Server-Sent Events (SSE)
  - Returns response chunks as they become available
  - Ideal for real-time, responsive chat interfaces

## Request Format

Both chat endpoints accept POST requests with the following JSON structure:

```json
{
  "message": "how to clean a dishwasher?",
  "session_id": "50e065d5-3020-4518-9b27-5e0e11a48260"
}
```

## Response Format

### Non-streaming endpoint (`/api/chat`)

Returns a complete JSON response:

```json
{
  "voiceSummary": "To clean a dishwasher, use vinegar and baking soda for a deep clean.",
  "displayResponse": "To clean a dishwasher using vinegar and baking soda, remove any dishes and racks from the dishwasher. Place a cup of white vinegar in a dishwasher-safe container on the top rack. Run a hot water cycle on the dishwasher to allow the vinegar to clean and disinfect the interior. Afterward, sprinkle a cup of baking soda on the bottom of the dishwasher and run another hot water cycle to deodorize and remove any remaining residue. For more details, visit the source at https://example.com/clean-dishwasher."
}
```

### Streaming endpoint (`/api/chat/stream`)

Returns a stream of Server-Sent Events (SSE), with each event containing chunks of the response. The request format is the same as the non-streaming endpoint:

```json
{
  "message": "how to clean a dishwasher?",
  "session_id": "50e065d5-3020-4518-9b27-5e0e11a48260"
}
```

The response is a stream of data chunks with the same structure as the non-streaming endpoint (containing `voiceSummary` and `displayResponse`), but delivered incrementally as Server-Sent Events.

## Setup and Running

Please refer to the [main README](../../README.md) for detailed setup and running instructions.

## Environment Variables

The server requires the following environment variables (typically set in `credentials.env`):

```bash
# Azure OpenAI Settings
AZURE_OPENAI_ENDPOINT=your_azure_openai_endpoint
AZURE_OPENAI_API_KEY=your_api_key
AZURE_OPENAI_API_VERSION=2024-05-01-preview
AZURE_OPENAI_MODEL_NAME=gpt-4o-mini
AZURE_OPENAI_VECTOR_STORE_ID=your_vector_store_id (if using vector store)

# Server Settings
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

## Development

### Running Tests

```bash
cd apps/botify_server
poetry run pytest
```

### Local Development

```bash
cd apps/botify_server
poetry install
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
