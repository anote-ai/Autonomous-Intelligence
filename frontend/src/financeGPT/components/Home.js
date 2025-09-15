import React, { Component, useState, useEffect, useRef } from "react";
import Chatbot from "./Chatbot";
import fetcher from "../../http/RequestConfig";
import { useNavigate } from "react-router-dom";
import ChatHistory from "./ChatHistory";
import Sidebar from "../Sidebar";
import { useDispatch } from "react-redux";
import { deductCreditsLocal } from "../../redux/UserSlice";

function HomeChatbot({
  isGuestMode = false,
  onRequestLogin,
  setIsLoggedInParent,
}) {
  const [selectedChatId, setSelectedChatId] = useState(isGuestMode ? 0 : null);
  const [forceUpdate, setForceUpdate] = useState(0);
  const [isPrivate, setIsPrivate] = useState(0);
  const [currChatName, setCurrChatName] = useState("");
  const [currTask, setcurrTask] = useState(0); //0 is file upload, 1 EDGAR, 2 mySQL db; have 0 be the default
  const [activeMessageIndex, setActiveMessageIndex] = useState(null);
  const [relevantChunk, setRelevantChunk] = useState("");
  const [menu, setMenu] = useState(false);
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(!isGuestMode);

  // Upload-related state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [triggerUpload, setTriggerUpload] = useState(false);
  const sidebarRef = useRef(null);
  const fileInputRef = useRef(null);
  const dispatch = useDispatch();

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
    if (isGuestMode) {
      // For guest mode, just set a default chat ID
      const guestChatId = 0;
      handleChatSelect(guestChatId);
      return guestChatId;
    }

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
        // Show error to user
        alert(response_data.error);
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

  // Handle upload trigger from chatbot - direct approach
  const handleUploadClick = (chatId) => {
    console.log("handleUploadClick called with chatId:", chatId);
    // If a chatId is provided, ensure selectedChatId is set
    if (chatId && chatId !== selectedChatId) {
      setSelectedChatId(chatId);
    }

    // Try direct file input first
    if (fileInputRef.current) {
      console.log("Triggering file input dialog");
      fileInputRef.current.click();
      return;
    }

    // Fallback to sidebar approach
    if (sidebarRef.current && sidebarRef.current.openFileDialog) {
      console.log("Using sidebar openFileDialog");
      sidebarRef.current.openFileDialog();
    } else {
      console.log("Using trigger upload fallback");
      // Fallback to trigger approach
      setTriggerUpload(true);
    }
  };

  // Handle file upload
  const handleFileUpload = async (event) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    if (!selectedChatId) {
      console.error("No chat selected for file upload");
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const formData = new FormData();
      for (let i = 0; i < files.length; i++) {
        formData.append("files[]", files[i]);
      }
      formData.append("chat_id", selectedChatId);

      console.log("Uploading files for chat:", selectedChatId);

      const response = await fetcher("ingest-pdf", {
        method: "POST",
        body: formData,
      });

      const responseData = await response.json();
      console.log("Upload response:", responseData);

      // Force update to refresh documents list
      handleForceUpdate();
    } catch (error) {
      console.error("File upload error:", error);
    } finally {
      setIsUploading(false);
      setUploadProgress(0);
      // Clear the file input
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  useEffect(() => {
    if (isGuestMode) {
      // For guest mode, don't retrieve chats from server
      setLoading(false);
      return;
    }

    const retrieveAllChats = async () => {
      console.log("i am in retrieve chats");
      setLoading(true);
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
      } finally {
        setLoading(false);
      }
    };
    retrieveAllChats();
  }, [forceUpdate, isGuestMode]);

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Main content area with proper top spacing */}
      <div className="flex-1 w-full h-full overflow-hidden flex">
        {/* Sidebar for chat history - show when menu is true and not in guest mode */}
        {!isGuestMode && <Sidebar handleChatSelect={handleChatSelect} />}
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
            currChatName={currChatName}
            confirmedModelKey={confirmedModelKey}
            setCurrChatName={setCurrChatName}
            activeMessageIndex={activeMessageIndex}
            setActiveMessageIndex={setActiveMessageIndex}
            setRelevantChunk={setRelevantChunk}
            isUploading={isUploading}
            uploadProgress={uploadProgress}
            onUploadClick={handleUploadClick}
            isGuestMode={isGuestMode}
          />
        </div>
      </div>
    </div>
  );
}

export default HomeChatbot;
