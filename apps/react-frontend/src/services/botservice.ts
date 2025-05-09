import { Message } from '../App';

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
  onStreamChunk?: (chunk: string) => void,
  onStreamEnd?: (chunk: StreamingBotChunk | null) => void,
): Promise<Message | null> => {
  const apiUrl = useStreaming
    ? `${backendApiPrefix}/api/chat/stream`
    : `${backendApiPrefix}/api/chat`;

  try {
    if (useStreaming) {
      const response = await fetch(apiUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Accept": "text/event-stream"
        },
        body: JSON.stringify({
          message: input,
          session_id: sessionId
        })
      });
      
      if (!response.ok) {
        throw new Error(`Stream request failed with status: ${response.status}`);
      }
      
      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error("Failed to get stream reader");
      }

      // SSE streams contain "data: {...}" lines
      const decoder = new TextDecoder();
      let buffer = "";
      let jsonResponse: StreamingBotChunk | null = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        
        // Process complete lines in buffer
        let lines = buffer.split('\n');
        buffer = lines.pop() || ""; // Keep the last (potentially incomplete) line
        
        for (const line of lines) {
          if (line.startsWith('data:')) {
            const dataStr = line.slice(5).trim();
            if (dataStr) {
              // Pass the raw chunk to the handler
              onStreamChunk?.(dataStr);
              
              // If this is valid JSON, save it for the final response
              if (dataStr.startsWith('{') && dataStr.endsWith('}')) {
                try {
                  const parsedJson = JSON.parse(dataStr);
                  jsonResponse = parsedJson;
                } catch (e) {
                  // Not valid JSON, ignore parsing error
                }
              }
            }
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
          message: input,
          session_id: sessionId 
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
