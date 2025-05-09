import { Message } from '../App';
import { makeStreamingJsonRequest } from "http-streaming-request";

const backendApiPrefix = import.meta.env.VITE_BACKEND_API_PREFIX;

if (!backendApiPrefix) {
  console.error('VITE_BACKEND_API_PREFIX is not defined in the environment variables.');
}

// Define the streaming chunk type based on backend response
export interface StreamingBotChunk {
  displayResponse?: string;
  [key: string]: unknown;
}

export const sendMessageToBot = async (
  input: string,
  useStreaming: boolean,
  sessionId: string,
  userId: string, // Keeping this parameter for now, but not using it as botify_server doesn't need it
  onStreamChunk?: (chunk: string) => void,
  onStreamEnd?: (chunk: StreamingBotChunk | null) => void,
): Promise<Message | null> => {
  const apiUrl = useStreaming
    ? `${backendApiPrefix}/api/chat/stream`
    : `${backendApiPrefix}/api/chat`;

  try {
    if (useStreaming) {
      // We'll implement streaming later as requested
      let lastDisplay = "";
      let jsonResponse: StreamingBotChunk | null = null;
      for await (const chunk of makeStreamingJsonRequest<StreamingBotChunk>({
        url: import.meta.env.VITE_BACKEND_API_PREFIX + "/api/chat/stream",
        method: "POST",
        payload: {
          input: { question: input },
          config: {
            configurable: {
              session_id: sessionId,
              user_id: userId,
            },
          },
        },
      })){
          jsonResponse=chunk;
          if (chunk && chunk.displayResponse) {
            // Only append new text
            const newText = chunk.displayResponse.slice(lastDisplay.length);
            if (newText) {
              lastDisplay = lastDisplay + newText;
              onStreamChunk?.(newText);
            }
          }
      }
      onStreamEnd?.(jsonResponse);
      return null; // No single message to return for streaming
    }
    else {
      // Updated to match botify_server API expectations
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: input,         // Changed from nested structure to match botify_server
          session_id: sessionId   // Changed from nested structure to match botify_server
          // Removed user_id as it's not used by the botify_server
        }),
      });

      if (!response.ok) {
        console.error(`API Error: ${response.status}`, await response.text().catch(() => ''));
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      
      // According to botify_server API docs, the response should look like:
      // { "voiceSummary": "summary", "displayResponse": "full response" }
      return {
        role: 'bot',
        content: data.displayResponse, // Direct access to displayResponse field
        timestamp: new Date().toISOString()
      };
    }
  } catch (error) {
    console.error('Error sending message to bot:', error);
    return null;
  }
};
