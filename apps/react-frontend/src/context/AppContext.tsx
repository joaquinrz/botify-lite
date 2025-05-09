import React, { createContext, useContext, useState, useEffect } from 'react';

interface AppContextType {
  useStreaming: boolean;
  setUseStreaming: (value: boolean) => void;
  useTextToSpeech: boolean;
  setUseTextToSpeech: (value: boolean) => void;
}

const defaultContextValue: AppContextType = {
  useStreaming: false,
  setUseStreaming: () => {},
  useTextToSpeech: true,
  setUseTextToSpeech: () => {}
};

export const AppContext = createContext<AppContextType>(defaultContextValue);

export const useAppContext = () => useContext(AppContext);

export const AppProvider: React.FC<{children: React.ReactNode}> = ({ children }: {children: React.ReactNode}) => {
  const [useStreaming, setUseStreaming] = useState(() => {
    const stored = localStorage.getItem('useStreaming');
    return stored ? JSON.parse(stored) : false;
  });

  const [useTextToSpeech, setUseTextToSpeech] = useState(() => {
    const stored = localStorage.getItem('useTextToSpeech');
    return stored ? JSON.parse(stored) : true; // Default to true for existing users
  });

  useEffect(() => {
    localStorage.setItem('useStreaming', JSON.stringify(useStreaming));
    console.log(`Streaming mode toggled: ${useStreaming}`);
  }, [useStreaming]);

  useEffect(() => {
    localStorage.setItem('useTextToSpeech', JSON.stringify(useTextToSpeech));
    console.log(`Text to Speech toggled: ${useTextToSpeech}`);
  }, [useTextToSpeech]);

  return (
    <AppContext.Provider value={{ 
      useStreaming, 
      setUseStreaming,
      useTextToSpeech,
      setUseTextToSpeech
    }}>
      {children}
    </AppContext.Provider>
  );
};
