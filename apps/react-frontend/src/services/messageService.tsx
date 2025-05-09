import { sendMessageToBot } from './botservice';
import { processMessageResponse, playSpeechResponse, handleStreamingChunk, handleStreamingComplete } from '../utils/messageUtils';
import { RecommendedProduct } from '../types';

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
  }: any,
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
        // Process the response
        const msgWithProducts = processMessageResponse(response);

        // Add the bot message with content (this was missing)
        updateOrAddBotMessage(response.content || response.generatedText || '');
        updateLastBotMessageWithProducts(msgWithProducts.recommendedProducts);

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
            updateOrAddBotMessage,
            setWaitingForProductRecs
          );
        },
        // JSON handler for final response
        async (json: { recommendedProducts?: RecommendedProduct[], displayResponse?: string } | null) => {
          // Don't update UI with displayResponse here - the handleStreamingComplete will do it
          // to avoid duplicate messages
          
          await handleStreamingComplete(
            json,
            updateLastBotMessageWithProducts,
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
