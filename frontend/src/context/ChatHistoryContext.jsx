import React, { createContext, useState, useCallback, useEffect } from "react";
import { chatAPI } from "../utils/api";

const ChatHistoryContext = createContext();

const ChatHistoryProvider = ({ children, isAuthenticated }) => {
  const [chatHistory, setChatHistory] = useState([]);
  const [isLoadingChats, setIsLoadingChats] = useState(false);
  const [deletedChatId, setDeletedChatId] = useState(null);

  const loadChatHistory = useCallback(async () => {
    if (!isAuthenticated) {
      setChatHistory([]);
      return;
    }

    setIsLoadingChats(true);
    try {
      const response = await chatAPI.getUserChats();
      setChatHistory(response.chats || []);
    } catch (error) {
      console.error("Error loading chat history:", error);
      setChatHistory([]);
    } finally {
      setIsLoadingChats(false);
    }
  }, [isAuthenticated]);

  const refreshChatHistory = useCallback(() => {
    if (isAuthenticated) {
      loadChatHistory();
    }
  }, [isAuthenticated, loadChatHistory]);

  const notifyDeletedChat = useCallback((chatId) => {
    setDeletedChatId(chatId);
  }, []);

  const clearDeletedChatId = useCallback(() => {
    setDeletedChatId(null);
  }, []);

  const clearChatHistory = useCallback(() => {
    setChatHistory([]);
    setDeletedChatId(null);
  }, []);

  const value = {
    chatHistory,
    isLoadingChats,
    loadChatHistory,
    refreshChatHistory,
    deletedChatId,
    notifyDeletedChat,
    clearDeletedChatId,
    clearChatHistory,
  };

  // Clear chat history when user logs out
  useEffect(() => {
    if (!isAuthenticated) {
      setChatHistory([]);
      setDeletedChatId(null);
    }
  }, [isAuthenticated]);

  return (
    <ChatHistoryContext.Provider value={value}>
      {children}
    </ChatHistoryContext.Provider>
  );
};

export { ChatHistoryContext, ChatHistoryProvider };
