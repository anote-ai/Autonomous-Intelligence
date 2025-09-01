import React, { Component, useState, useEffect, useRef } from "react";
import Navbarchatbot from "./NavbarChatbot";
import Chatbot from "./Chatbot";
import "../styles/Chatbot.css";
import SidebarChatbot from "./SidebarChatbot";
import fetcher from "../../http/RequestConfig";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import Popout from "./Popout";
import ChatHistory from "./ChatHistory";
import BackendStatusIndicator from "../../components/BackendStatusIndicator";

function HomeChatbot({ isGuestMode = false, onRequestLogin, setIsLoggedInParent }) {
  const [selectedChatId, setSelectedChatId] = useState(isGuestMode ? 0 : null);
  const [forceUpdate, setForceUpdate] = useState(0);
  const [isPrivate, setIsPrivate] = useState(0);
  const [currChatName, setCurrChatName] = useState("");
  const [currTask, setcurrTask] = useState(0); //0 is file upload, 1 EDGAR, 2 mySQL db; have 0 be the default
  const [showChatbot, setShowChatbot] = useState(false);
  const [isEdit, setIsEdit] = useState(0);
  const [activeMessageIndex, setActiveMessageIndex] = useState(null);
  const [relevantChunk, setRelevantChunk] = useState("");
  const [menu, setMenu] = useState(false);
  const [chats, setChats] = useState([]);
  const navigate = useNavigate();
  const [loading, setLoading] = useState(!isGuestMode);
  const { id } = useParams();
  const location = useLocation();

  // Upload-related state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [triggerUpload, setTriggerUpload] = useState(false);
  const sidebarRef = useRef(null);
  const fileInputRef = useRef(null);

  const handleMenu = () => {
    setMenu((prev) => !prev);
  };
  const [confirmedModelKey, setConfirmedModelKey] = useState("");

  const handleChatSelect = (chatId) => {
    console.log("select")
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
      const response = await fetcher("create-new-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_type: currTask, model_type: isPrivate }),
      });

      const response_data = await response.json();
      handleChatSelect(response_data.chat_id);
      return response_data.chat_id;
    } catch (error) {
      // Only log errors that aren't silent network errors
      if (!error.silent) {
        console.error("Error creating new chat:", error);
      }
      if (error.type === 'NETWORK_ERROR') {
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

  // Reset upload trigger (called by sidebar after handling)
  const resetUploadTrigger = () => {
    setTriggerUpload(false);
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
        fileInputRef.current.value = '';
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
        if (error.type !== 'NETWORK_ERROR') {
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
      {/* Backend Status Indicator */}
      <BackendStatusIndicator />

      {/* ChatGPT-style top navigation */}
      <Navbarchatbot
        selectedChatId={selectedChatId}
        onChatSelect={handleChatSelect}
        handleForceUpdate={handleForceUpdate}
        isPrivate={isPrivate}
        loading={loading}
        setIsPrivate={setIsPrivate}
        menu={menu}
        handleMenu={handleMenu}
        chats={chats}
        setcurrTask={setcurrTask}
        currTask={currTask}
        setConfirmedModelKey={setConfirmedModelKey}
        confirmedModelKey={confirmedModelKey}
        setCurrChatName={setCurrChatName}
        setIsEdit={setIsEdit}
        setShowChatbot={setShowChatbot}
        createNewChat={createNewChat}
        handleChatSelect={handleChatSelect}
        forceUpdate={forceUpdate}
        isGuestMode={isGuestMode}
        onRequestLogin={onRequestLogin}
        setIsLoggedInParent={setIsLoggedInParent}
      />

      {/* Main content area with proper top spacing */}
      <div className="flex-1 w-full pt-16 h-full overflow-hidden flex">
        {/* Sidebar for chat history - show when menu is true and not in guest mode */}
        {menu && !isGuestMode && (
          <div className="w-80 border-r border-gray-700 bg-gray-800 flex-shrink-0">
            <div className="border-t border-gray-700 pt-4">
              <div className="px-2">
                <ChatHistory
                  chats={chats}
                  selectedChatId={selectedChatId}
                  handleChatSelect={handleChatSelect}
                  handleForceUpdate={handleForceUpdate}
                />
              </div>
            </div>
          </div>
        )}

        {/* Chat area */}
        <div className="flex-1 h-full">
          {currTask === 0 && (
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
          )}
        </div>
      </div>

      {/* Hidden file input for direct upload */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileUpload}
        accept=".pdf,.doc,.docx,.txt,.csv"
        multiple
        style={{ display: "none" }}
      />
    </div>
  );
}

export default HomeChatbot;
