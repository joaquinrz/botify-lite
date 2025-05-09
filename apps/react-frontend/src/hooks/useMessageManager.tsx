import { useState, useRef } from 'react';
import { Message, RecommendedProduct } from '../types';

export function useMessageManager() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isWaitingForBotResponse, setIsWaitingForBotResponse] = useState(false);
  const [isWaitingForProductRecs, setIsWaitingForProductRecs] = useState(false);
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
  
  const updateLastBotMessageWithProducts = (products: RecommendedProduct[] | undefined) => {
    setMessages(prev => {
      const updatedMessages = [...prev];
      // Find the last bot message
      let lastBotIdx = -1;
      for (let i = updatedMessages.length - 1; i >= 0; i--) {
        if (updatedMessages[i].role === 'bot') {
          lastBotIdx = i;
          break;
        }
      }
      
      if (lastBotIdx !== -1) {
        // Attach the recommendedProducts array to the message for rendering product cards
        updatedMessages[lastBotIdx] = {
          ...updatedMessages[lastBotIdx],
          recommendedProducts: products || []
        };
      }
      return updatedMessages;
    });
  };
  
  const resetWaitingStates = () => {
    setIsWaitingForBotResponse(false);
    setIsWaitingForProductRecs(false);
  };
  
  const setWaitingForBot = () => {
    setIsWaitingForBotResponse(true);
    setIsWaitingForProductRecs(false);
    botMessageCreatedRef.current = false;
  };
  
  const setWaitingForProductRecs = () => {
    setIsWaitingForBotResponse(false);
    setIsWaitingForProductRecs(true);
  };

  return {
    messages,
    isWaitingForBotResponse,
    isWaitingForProductRecs,
    botMessageCreatedRef,
    addUserMessage,
    addBotMessage,
    updateOrAddBotMessage,
    updateLastBotMessageWithProducts,
    resetWaitingStates,
    setWaitingForBot,
    setWaitingForProductRecs
  };
}
