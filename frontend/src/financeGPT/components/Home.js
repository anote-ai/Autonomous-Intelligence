import React, { useState, useEffect } from "react";
import Chatbot from "./Chatbot";
import fetcher from "../../http/RequestConfig";
import Sidebar from "../Sidebar";
function HomeChatbot({ isGuestMode = false }) {
  const [selectedChatId, setSelectedChatId] = useState(isGuestMode ? 0 : null);
  const [forceUpdate, setForceUpdate] = useState(0);
  const [isPrivate, setIsPrivate] = useState(0);
  const [currChatName, setCurrChatName] = useState("");
  const [currTask, setcurrTask] = useState(0); //0 is file upload, 1 EDGAR, 2 mySQL db; have 0 be the default
  const [activeMessageIndex, setActiveMessageIndex] = useState(null);
  const [menu, setMenu] = useState(false);
  const [chats, setChats] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  const showError = (message) => {
    setErrorMessage(message);
    // Auto-clear error after 5 seconds
    setTimeout(() => setErrorMessage(""), 5000);
  };

  const handleMenu = () => {
    setMenu((prev) => !prev);
  };
  const [confirmedModelKey] = useState("");

  const handleChatSelect = (chatId) => {
    console.log("select");
    setSelectedChatId(chatId);
  };

  const handleForceUpdate = () => {
    setForceUpdate((prev) => prev + 1);
  };

  const createNewChat = async () => {
    try {
      // Then create the chat
      const response = await fetcher("create-new-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_type: currTask, model_type: isPrivate }),
      });

      const response_data = await response.json();

      // Check if the response contains an error
      if (response_data.error) {
        // Show error to user with proper notification
        showError(response_data.error);
        throw new Error(response_data.error);
      }

      handleChatSelect(response_data.chat_id);
      return response_data.chat_id;
    } catch (error) {
      // Only log errors that aren't silent network errors
      if (!error.silent) {
        console.error("Error creating new chat:", error);
      }
      if (error.type === "NETWORK_ERROR") {
        // Backend is offline, create a temporary local chat ID
        const tempChatId = Date.now(); // Use timestamp as temp ID
        handleChatSelect(tempChatId);
        return tempChatId;
      }
      throw error; // Re-throw non-network errors
    }
  };

  useEffect(() => {
    if (isGuestMode) {
      // For guest mode, don't retrieve chats from server
      return;
    }

    const retrieveAllChats = async () => {
      console.log("i am in retrieve chats");
      try {
        const response = await fetcher("retrieve-all-chats", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ chat_type: 0 }),
        });

        const response_data = await response.json();
        setChats(response_data.chat_info);
        console.log("retriving data", response_data);
      } catch (error) {
        // Only log errors that aren't silent network errors
        if (!error.silent) {
          console.error("Error fetching chats:", error);
        }
        // If it's a network error (backend down), don't show error UI
        // Just keep the existing state and let the user know backend is offline
        if (error.type !== "NETWORK_ERROR") {
          // Handle other types of errors if needed
          if (!error.silent) {
            console.error("Non-network error:", error);
          }
        }
      }
    };
    retrieveAllChats();
  }, [forceUpdate, isGuestMode]);

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
            handleToggleSidebar={handleMenu}
            handleChatSelect={handleChatSelect}
          />
        )}
        {/* Chat area */}
        <div className="flex-1 h-full">
          <Chatbot
            chat_type={currTask}
            selectedChatId={selectedChatId}
            handleChatSelect={handleChatSelect}
            handleMenu={handleMenu}
            chats={chats}
            createNewChat={createNewChat}
            menu={menu}
            handleForceUpdate={handleForceUpdate}
            forceUpdate={forceUpdate}
            isPrivate={isPrivate}
            confirmedModelKey={confirmedModelKey}
            setCurrChatName={setCurrChatName}
            activeMessageIndex={activeMessageIndex}
            setActiveMessageIndex={setActiveMessageIndex}
            isGuestMode={isGuestMode}
          />
        </div>
      </div>
    </div>
  );
}

export default HomeChatbot;
