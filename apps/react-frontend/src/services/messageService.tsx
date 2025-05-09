import { sendMessageToBot } from './botservice';
import { processMessageResponse, playSpeechResponse, handleStreamingChunk, handleStreamingComplete } from '../utils/messageUtils';
import { Message, RecommendedProduct } from '../types';

export const processUserInput = async (
  userInput: string,
  useStreaming: boolean,
  {
    addUserMessage,
    updateOrAddBotMessage,
    updateLastBotMessageWithProducts,
    resetWaitingStates,
    setWaitingForBot,
    setWaitingForProductRecs
  }: any
) => {
  if (!userInput.trim()) return;

  // Add user message
  addUserMessage(userInput);

  // Set states
  setWaitingForBot();

  try {
    const sessionId = "session-id-placeholder";
    const userId = "user-id-placeholder";
    const speechService = await import('./speechService');

    if (!useStreaming) {
      // Non-streaming mode
      const response = await sendMessageToBot(userInput, useStreaming, sessionId, userId);
      if (response) {
        // Process the response
        const msgWithProducts = processMessageResponse(response);

        // Add the bot message with content (this was missing)
        updateOrAddBotMessage(response.content || response.generatedText || '');
        updateLastBotMessageWithProducts(msgWithProducts.recommendedProducts);

        // Play speech response
        await playSpeechResponse(response, speechService);
      }
      resetWaitingStates();
    } else {
      // Streaming mode
      await sendMessageToBot(
        userInput,
        useStreaming,
        sessionId,
        userId,
        // Chunk handler for streaming text
        (chunk: string) => {
          handleStreamingChunk(
            chunk,
            updateOrAddBotMessage,
            setWaitingForProductRecs
          );
        },
        // JSON handler for product recommendations
        async (json: { recommendedProducts?: RecommendedProduct[] } | null) => {
          await handleStreamingComplete(
            json,
            updateLastBotMessageWithProducts,
            speechService
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
