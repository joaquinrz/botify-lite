import { Message } from '../types';

export const processMessageResponse = (response: any) => {
  const msgWithProducts = { ...response, timestamp: new Date().toISOString() };

  try {
    const parsed = JSON.parse(response.content);
    if (parsed?.recommendedProducts?.length) {
      msgWithProducts.recommendedProducts = parsed.recommendedProducts;
      if (parsed.displayResponse) {
        msgWithProducts.content = parsed.displayResponse;
      }
    }
  } catch {
    // Parsing failed, ignore
  }

  return msgWithProducts;
};

export const playSpeechResponse = async (response: any, speechService: any) => {
  try {
    const voiceSummary = speechService.extractVoiceSummaryFromResponse(response);
    if (voiceSummary) {
      await speechService.synthesizeSpeech(voiceSummary);
    } else if (response.content) {
      await speechService.synthesizeSpeech(response.content);
    }
  } catch (error) {
    console.error('Error playing voice response:', error);
  }
};

export const handleStreamingChunk = (
  chunk: string,
  updateOrAddBotMessage: (content: string) => void,
  setWaitingForProductRecs: () => void
) => {
  // Skip empty chunks
  if (!chunk || chunk.trim() === '') return;

  // Log the chunk for debugging
  console.log('Processing chunk:', chunk);

  try {
    // Update messages with chunk
    updateOrAddBotMessage(chunk);

    // Only set waiting for product recs if needed
    if (chunk.includes('RECOMMENDED_PRODUCTS_PLACEHOLDER') ||
        chunk.includes('Looking for product recommendations...')) {
      setWaitingForProductRecs();
    }
  } catch (error) {
    console.error('Error handling streaming chunk:', error);
  }
};

export const handleStreamingComplete = async (
  json: { recommendedProducts?: any[] } | null,
  updateLastBotMessageWithProducts: (products: any[] | undefined) => void,
  speechService: any
) => {
  if (json !== null) {
    console.log('Streaming completed with JSON:', json);

    // Add product recommendations
    updateLastBotMessageWithProducts(json.recommendedProducts);

    // Play voice summary if available
    try {
      const voiceSummary = speechService.extractVoiceSummaryFromResponse(json);
      if (voiceSummary) {
        await speechService.synthesizeSpeech(voiceSummary);
      }
    } catch (speechError) {
      console.error('Error playing voice response:', speechError);
    }
  }
};
