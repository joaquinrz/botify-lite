# React Frontend for Botify Lite

This is the React-based frontend for the Botify Lite application. It provides a chat interface for interacting with the Botify Lite AI bot

## Features

- Chatbot UI with support for both streaming and non-streaming responses
- Real-time updates and smooth scrolling
- Environment-based configuration

## Getting Started

### 1. Install dependencies

```bash
yarn install

```

### 2. Create a `.env` file

Create a `.env` file in the `react-frontend` directory with the following content:

```text
VITE_BACKEND_API_PREFIX=http://localhost:8080
VITE_TOKEN_SERVICE_PREFIX=http://localhost:8081
```

- Change the URL if your backend is running elsewhere.

### 3. Run the development server

```bash
yarn run dev
```

This will start the Vite development server. By default, the app will be available at [http://localhost:5173](http://localhost:5173).

## Usage

- Type your message in the chat input and press Enter or click Send.
- Toggle streaming mode in the settings drawer (top right gear icon).
- When the bot recommends products, they will appear as cards below the response.

## Project Structure

- `src/` - Main source code
  - `components/` - React components (ChatContainer, ProductCard, etc.)
  - `services/` - API and bot service logic
  - `App.tsx` - Main app logic
- `.env` - Environment variables for local development

## Notes

- Make sure your backend (bot-service) and token-service are running and accessible at the URL specified in `VITE_BACKEND_API_PREFIX` and `VITE_TOKEN_SERVICE_PREFIX`.
- For Docker-based development, see the root `docker-compose.yaml`.

---

For more details, see the main project README or contact the maintainers.
