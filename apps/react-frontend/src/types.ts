export interface Message {
  role: string;
  content: string;
  timestamp: string;
  voiceSummary?: string; // Optional field for text-to-speech
}

export interface MessageManagerHook {
  messages: Message[];
  isWaitingForBotResponse: boolean;
  botMessageCreatedRef: React.MutableRefObject<boolean>;
  addUserMessage: (content: string) => Message;
  addBotMessage: (botMessage: Message) => void;
  updateOrAddBotMessage: (content: string) => void;
  resetWaitingStates: () => void;
  setWaitingForBot: () => void;
}

export interface StreamingResponse {
  displayResponse?: string;
  voiceSummary?: string;
  [key: string]: unknown;
}

export interface SpeechService {
  startSpeechRecognition: () => Promise<string>;
  stopSpeechRecognition: () => Promise<string | null>;
  synthesizeSpeech: (text: string) => Promise<void>;
  extractVoiceSummaryFromResponse: (response: StreamingResponse | any) => string | null;
}
