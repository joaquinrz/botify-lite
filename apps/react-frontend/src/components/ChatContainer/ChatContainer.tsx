import React, { useEffect, useRef } from 'react';
import './ChatContainer.css';
import InputContainer from '../InputContainer/InputContainer';
import { Message } from '../../types';

interface ChatContainerProps {
  messages: Message[];
  input: string;
  setInput: (value: string) => void;
  handleKeyPress: (e: React.KeyboardEvent<HTMLTextAreaElement>) => void;
  sendMessage: () => void;
  handleMicrophoneClick: () => void;
  isWaitingForBotResponse: boolean;
  isListening?: boolean;
}

const ChatContainer: React.FC<ChatContainerProps> = ({
  messages,
  input,
  setInput,
  handleKeyPress,
  sendMessage,
  handleMicrophoneClick,
  isWaitingForBotResponse,
  isListening = false,
}) => {
  const lastMessageRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const lastMessageContent = messages[messages.length - 1]?.content;

  useEffect(() => {
    // Always scroll to the bottom of the messages container when messages or waiting states change
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages.length, lastMessageContent, isWaitingForBotResponse]);

  return (
    <div className="chat-container">
      <div className="messages-container">
        <div className="messages">
          {messages.map((msg, index) => {
            let displayContent = msg.content;
            // Prevent accidental rendering of [object Object] if content is an object or contains [object Object]
            if (typeof displayContent !== 'string') {
              displayContent = '';
            } else if (displayContent.includes('[object Object]')) {
              displayContent = displayContent.replace(/\[object Object\]/g, '');
            }
            return (
              <div
                key={index}
                className={msg.role === 'user' ? 'user-message' : 'bot-message'}
                ref={index === messages.length - 1 ? lastMessageRef : undefined}
              >
                <div className="message-timestamp">
                  {new Date(msg.timestamp).toLocaleString([], { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                </div>
                <div className="message-content">
                  {displayContent.split('\n').map((line, i) => <div key={i}>{line}</div>)}
                </div>
              </div>
            );
          })}
          {isWaitingForBotResponse && (
            <div className="bot-message waiting-indicator">
              <span></span>
              <span></span>
              <span></span>
              <span></span>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>
      <InputContainer
        input={input}
        setInput={setInput}
        handleKeyPress={handleKeyPress}
        sendMessage={sendMessage}
        handleMicrophoneClick={handleMicrophoneClick}
        isListening={isListening}
      />
    </div>
  );
};

export default ChatContainer;
