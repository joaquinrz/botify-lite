import { useState, useRef } from 'react';
import { Message } from '../types';

export function useMessageManager() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  const botMessageCreatedRef = useRef(false);
  
  const addUserMessage = (content: string) => {
    const userMessage: Message = { 
      role: 'user', 
      content, 
      timestamp: new Date().toISOString() 
    };
    setMessages(prev => [...prev, userMessage]);
    return userMessage;
  };
  
  const addBotMessage = (botMessage: Message) => {
    setMessages(prev => [...prev, botMessage]);
  };
  
  const updateOrAddBotMessage = (content: string) => {
    setMessages(prev => {
      const updatedMessages = [...prev];
      const lastBotIndex = updatedMessages.findIndex(
        (msg, i) => msg.role === 'bot' && i === updatedMessages.length - 1
      );
      
      if (lastBotIndex === -1) {
        // Add new bot message
        return [...updatedMessages, {
          role: 'bot',
          content: content,
          timestamp: new Date().toISOString()
        }];
      } else {
        // Update existing bot message
        const updatedMsg = {
          ...updatedMessages[lastBotIndex],
          content: updatedMessages[lastBotIndex].content + content
        };
        return [
          ...updatedMessages.slice(0, lastBotIndex),
          updatedMsg,
          ...updatedMessages.slice(lastBotIndex + 1)
        ];
      }
    });
  };
  
  const resetWaitingStates = () => {
    setIsWaitingForBotResponse(false);
  };
  
  const setWaitingForBot = () => {
    setIsWaitingForBotResponse(true);
    botMessageCreatedRef.current = false;
  };

  return {
    messages,
    isWaitingForBotResponse,
    botMessageCreatedRef,
    addUserMessage,
    addBotMessage,
    updateOrAddBotMessage,
    resetWaitingStates,
    setWaitingForBot
  };
}
