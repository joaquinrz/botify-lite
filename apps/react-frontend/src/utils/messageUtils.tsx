import { Message, StreamingResponse, SpeechService } from '../types';

export const processMessageResponse = (response: any) => {
  const processedMessage = { ...response, timestamp: new Date().toISOString() };

  try {
    const parsed = JSON.parse(response.content);
    if (parsed?.displayResponse) {
      processedMessage.content = parsed.displayResponse;
    }
    // Carry voiceSummary through for TTS
    if (parsed?.voiceSummary) {
      processedMessage.voiceSummary = parsed.voiceSummary;
    }
  } catch {
    // Parsing failed, ignore
  }

  return processedMessage;
};

export const playSpeechResponse = async (
  response: Message | StreamingResponse | any, 
  speechService: any, 
  useTextToSpeech: boolean = true
) => {
  if (!useTextToSpeech) {
    console.log('Text to Speech is disabled, skipping audio playback');
    return;
  }

  try {
    const voiceSummary = speechService.extractVoiceSummaryFromResponse(response);
    if (voiceSummary) {
      await speechService.synthesizeSpeech(voiceSummary);
    } else if (response.content && typeof response.content === 'string') {
      await speechService.synthesizeSpeech(response.content);
    }
  } catch (error) {
    console.error('Error playing voice response:', error);
  }
};

// Keep track of accumulated JSON outside the function
let accumulatedJsonString = '';
let isCollectingJson = false;

export const handleStreamingChunk = (
  chunk: string,
  updateOrAddBotMessage: (content: string) => void
) => {
  // Skip empty chunks
  if (!chunk || chunk.trim() === '') return;

  // Log the chunk for debugging
  console.log('Processing chunk:', chunk);

  try {
    // If this is the start of a JSON object, begin collecting
    if (chunk === '{') {
      isCollectingJson = true;
      accumulatedJsonString = '{';
      return; // Don't display the opening brace
    }
    
    // If we're collecting a JSON object
    if (isCollectingJson) {
      accumulatedJsonString += chunk;
      
      // Check if this completes the JSON object
      if (chunk === '}') {
        isCollectingJson = false;
        try {
          // Try to parse the complete JSON
          const jsonObject = JSON.parse(accumulatedJsonString);
          
          // If it has displayResponse, use that
          if (jsonObject.displayResponse) {
            const formattedMessage = jsonObject.displayResponse
              .replace(/([a-z])([A-Z])/g, '$1 $2') // Add spaces between camelCase words
              .replace(/([.!?])([A-Z])/g, '$1 $2'); // Add spaces after punctuation
              
            // Update the UI with the complete text
            updateOrAddBotMessage(formattedMessage);
            return;
          }
        } catch (jsonError) {
          console.error('Failed to parse collected JSON:', jsonError);
        }
        
        // Reset accumulation
        accumulatedJsonString = '';
      }
      
      // Don't display raw JSON chunks
      return;
    }
    
    // For non-JSON text chunks or if JSON parsing failed, display directly
    updateOrAddBotMessage(chunk);
  } catch (error) {
    console.error('Error handling streaming chunk:', error);
  }
};

export const handleStreamingComplete = async (
  json: StreamingResponse | null,
  speechService: any,
  useTextToSpeech: boolean = true
) => {
  if (json !== null) {
    console.log('Streaming completed with JSON:', json);

    // If we have a displayResponse that needs formatting
    if (typeof json.displayResponse === 'string') {
      // Check if it's a raw string that needs formatting
      if (!json.displayResponse.includes(' ') && json.displayResponse.length > 15) {
        // Format the message with proper spacing for camelCase text
        const formattedText = json.displayResponse
          .replace(/([a-z])([A-Z])/g, '$1 $2')
          .replace(/([.!?])([A-Z])/g, '$1 $2');
        
        // Replace the message with the properly formatted version
        json.displayResponse = formattedText;
      }
    }
    
    // Reset the variables used for chunk accumulation
    accumulatedJsonString = '';
    isCollectingJson = false;

    // Play voice summary if available and Text to Speech is enabled
    if (useTextToSpeech) {
      try {
        const voiceSummary = speechService.extractVoiceSummaryFromResponse(json);
        if (voiceSummary) {
          await speechService.synthesizeSpeech(voiceSummary);
        }
      } catch (speechError) {
        console.error('Error playing voice response:', speechError);
      }
    } else {
      console.log('Text to Speech is disabled, skipping audio playback');
    }
  }
};
