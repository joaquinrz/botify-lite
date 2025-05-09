import { sendMessageToBot, StreamingBotChunk } from './botservice';
import { playSpeechResponse, handleStreamingChunk, handleStreamingComplete } from '../utils/messageUtils';
import { MessageManagerHook, StreamingResponse } from '../types';

export const processUserInput = async (
  userInput: string,
  useStreaming: boolean,
  {
    addUserMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot
  }: MessageManagerHook,
  useTextToSpeech: boolean = true
) => {
  if (!userInput.trim()) return;

  // Add user message
  addUserMessage(userInput);

  // Set states
  setWaitingForBot();

  try {
    const sessionId = "session-id-placeholder";
    const speechService = await import('./speechService');

    if (!useStreaming) {
      // Non-streaming mode
      const response = await sendMessageToBot(userInput, useStreaming, sessionId);
      if (response) {
        // Add the bot message with content
        updateOrAddBotMessage(response.content || response.generatedText || '');

        // Play speech response if enabled
        await playSpeechResponse(response, speechService, useTextToSpeech);
      }
      resetWaitingStates();
    } else {
      // Streaming mode
      await sendMessageToBot(
        userInput,
        useStreaming,
        sessionId,
        // Chunk handler for streaming text
        (chunk: string) => {
          handleStreamingChunk(
            chunk,
            updateOrAddBotMessage
          );
        },
        // JSON handler for final response
        async (json: StreamingResponse | null) => {
          await handleStreamingComplete(
            json,
            speechService,
            useTextToSpeech
          );
          resetWaitingStates();
        }
      );
    }
  } catch (error) {
    console.error('Error processing message:', error);
    resetWaitingStates();
  }
};
