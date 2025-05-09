export interface Message {
  role: string;
  content: string;
  timestamp: string;
  voiceSummary?: string; // Optional field for text-to-speech
}
