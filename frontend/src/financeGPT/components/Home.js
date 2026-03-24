import React, { useState, useEffect } from "react";
import Chatbot from "./Chatbot";
import Sidebar from "../Sidebar";
import { useChatHistory } from "../useChatHistory";

function HomeChatbot({
  isGuestMode = false,
  onSidebarCollapsedChange = () => {},
}) {
  const [selectedChatId, setSelectedChatId] = useState(isGuestMode ? 0 : null);
  // Default expanded on desktop (md+), collapsed on mobile
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(
    () => window.innerWidth < 768
  );
  const [errorMessage, setErrorMessage] = useState("");
  const isPrivate = 0;
  const currTask = 0;
  const { chats, loading: chatsLoading, refreshChats, createChat, renameChatById, deleteChatById } =
    useChatHistory({
      enabled: !isGuestMode,
    });

  const showError = (message) => {
    setErrorMessage(message);
    // Auto-clear error after 5 seconds
    setTimeout(() => setErrorMessage(""), 5000);
  };

  const handleChatSelect = (chatId) => {
    setSelectedChatId(chatId);
  };

  const handleSidebarToggle = () => {
    setIsSidebarCollapsed((prev) => {
      const nextState = !prev;
      onSidebarCollapsedChange(nextState);
      return nextState;
    });
  };

  const createNewChat = async () => {
    try {
      const chatId = await createChat({ chatType: currTask, modelType: isPrivate });
      handleChatSelect(chatId);
      return chatId;
    } catch (error) {
      if (!error.silent) console.error("Error creating new chat:", error);
      if (error.type === "NETWORK_ERROR") {
        const tempChatId = Date.now();
        handleChatSelect(tempChatId);
        return tempChatId;
      }
      showError(error.message || "Failed to create chat");
      throw error;
    }
  };

  useEffect(() => {
    setSelectedChatId(isGuestMode ? 0 : null);

    if (isGuestMode) {
      onSidebarCollapsedChange(true);
    }
  }, [isGuestMode, onSidebarCollapsedChange]);

  return (
    <div className="h-screen flex flex-col bg-primary">
      {/* Error notification */}
      {errorMessage && (
        <div className="fixed top-4 left-1/2 transform -translate-x-1/2 z-50 bg-red-600 text-white px-6 py-3 rounded-lg shadow-lg border border-red-500 max-w-md">
          <div className="flex items-center justify-between">
            <span className="text-sm">{errorMessage}</span>
            <button
              onClick={() => setErrorMessage("")}
              className="ml-4 text-white hover:text-red-200 text-lg font-bold"
            >
              ×
            </button>
          </div>
        </div>
      )}
      {/* Main content area with proper top spacing */}
      <div className="flex-1 w-full h-full overflow-hidden flex">
        {/* Sidebar for chat history - show when menu is true and not in guest mode */}
        {!isGuestMode && (
          <Sidebar
            handleChatSelect={handleChatSelect}
            isCollapsed={isSidebarCollapsed}
            onToggle={handleSidebarToggle}
            chats={chats}
            chatsLoading={chatsLoading}
            onRefreshChats={refreshChats}
            onRenameChat={renameChatById}
            onDeleteChat={deleteChatById}
          />
        )}
        {/* Chat area */}
        <div className="flex-1 h-full">
          <Chatbot
            chat_type={currTask}
            selectedChatId={selectedChatId}
            handleChatSelect={handleChatSelect}
            createNewChat={createNewChat}
            isPrivate={isPrivate}
            isGuestMode={isGuestMode}
            onChatsChanged={refreshChats}
          />
        </div>
      </div>
    </div>
  );
}

export default HomeChatbot;
