import React, { useState, useRef, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useTheme } from "../../hooks/useTheme";
import { useChatHistory } from "../../hooks/useChatHistory";
import TextBox from "./TextBox";
import ChatMessages from "./ChatMessages";
import Toast from "../common/Toast";
import useAutoResizeTextarea from "../../hooks/useAutoResizeTextarea";
import { chatAPI, API_SERVER_URL } from "../../utils/api";
import { FILE_ATTACHMENT_INDICATOR } from "../../constants/messages";

const ChatInterface = ({ isSidebarOpen, isAuthenticated }) => {
  const { chatId, shareId } = useParams();
  const navigate = useNavigate();
  const { theme } = useTheme();
  const { refreshChatHistory, deletedChatId, clearDeletedChatId } =
    useChatHistory();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [currentChatId, setCurrentChatId] = useState(chatId || null);
  const [isSending, setIsSending] = useState(false);
  const [isLoadingMessages, setIsLoadingMessages] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [errorNotification, setErrorNotification] = useState(null);
  const loadedChatIdRef = useRef(null);

  // Auto-resize textarea using custom hook
  const textareaRef = useAutoResizeTextarea(inputValue, 4);

  // Load messages from database when chatId changes
  const loadShareChatMessage = async (shareIdToLoad) => {
    if (!shareIdToLoad) return;

    setIsLoadingMessages(true);
    setLoadError(null);

    try {
      const response = await chatAPI.getSharedChat(shareIdToLoad);
      const loadedMessages = response.messages.map((msg) => ({
        id: msg.id,
        text: msg.content,
        sender: msg.role === "user" ? "user" : "assistant",
        timestamp: msg.created_at,
        files: msg.files
          ? msg.files.map((f) => ({
              name: f.name,
              url: `${API_SERVER_URL}${f.url}`,
              type: f.type,
              size: f.size,
            }))
          : [],
      }));

      setMessages(loadedMessages);
      loadedChatIdRef.current = shareIdToLoad;
    } catch (error) {
      setIsLoadingMessages(false);
      console.error("Error loading shared chat:", error);
      setLoadError(error.message || "Failed to load shared chat");
    } finally {
      setIsLoadingMessages(false);
    }
  };
  const loadChatMessages = async (chatIdToLoad) => {
    if (!chatIdToLoad) return;

    setIsLoadingMessages(true);
    setLoadError(null);

    try {
      const response = await chatAPI.getChat(chatIdToLoad);
      const loadedMessages = response.messages.map((msg) => ({
        id: msg.id,
        text: msg.content,
        sender: msg.role === "user" ? "user" : "assistant",
        timestamp: msg.created_at,
        files: msg.files
          ? msg.files.map((f) => ({
              name: f.name,
              url: `${API_SERVER_URL}${f.url}`,
              type: f.type,
              size: f.size,
            }))
          : [],
      }));

      setMessages(loadedMessages);
      loadedChatIdRef.current = chatIdToLoad;
    } catch (err) {
      console.error("Error loading messages:", err);

      // If chat not found (404) or unauthorized, redirect to home only if not already there
      if (
        (err.status === 404 || err.status === 401 || err.status === 403) &&
        chatIdToLoad
      ) {
        // Reset state before redirecting
        setMessages([]);
        setCurrentChatId(null);
        loadedChatIdRef.current = null;
        navigate("/", { replace: true });
      } else {
        setLoadError(err.message);
      }
    } finally {
      setIsLoadingMessages(false);
    }
  };

  // Check if current chat was deleted
  useEffect(() => {
    if (deletedChatId && chatId === deletedChatId) {
      // Clear state and navigate to home
      setMessages([]);
      setCurrentChatId(null);
      loadedChatIdRef.current = null;
      clearDeletedChatId();
      navigate("/", { replace: true });
    }
  }, [deletedChatId, chatId, clearDeletedChatId, navigate]);

  // Clear state when user logs out
  useEffect(() => {
    if (!isAuthenticated && !shareId) {
      setMessages([]);
      setInputValue("");
      setUploadedFiles([]);
      setCurrentChatId(null);
      setLoadError(null);
      navigate("/");
      loadedChatIdRef.current = null;
    }
  }, [isAuthenticated, navigate, shareId]);

  // Check if chatId has changed and load messages
  useEffect(() => {
    if (shareId && shareId !== loadedChatIdRef.current && !isLoadingMessages) {
      setMessages([]);
      setLoadError(null);
      setCurrentChatId(shareId);
      loadShareChatMessage(shareId);
    } else if (
      chatId &&
      chatId !== loadedChatIdRef.current &&
      !isLoadingMessages
    ) {
      // Reset state when switching chats
      setMessages([]);
      setLoadError(null);
      setCurrentChatId(chatId);
      loadChatMessages(chatId);
    } else if (!chatId && !shareId && loadedChatIdRef.current !== null) {
      // Clear messages when navigating to home
      setMessages([]);
      setCurrentChatId(null);
      loadedChatIdRef.current = null;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [chatId, shareId, isLoadingMessages]);

  const handleFileSelect = (files, type) => {
    console.log(`Selected ${type}:`, files);

    // Store files locally, don't upload yet
    setUploadedFiles((prev) => [
      ...prev,
      ...files.map((file) => ({
        id: Date.now() + Math.random(),
        file: file,
        type,
        name: file.name,
        url: URL.createObjectURL(file),
        fileType: file.type,
        size: file.size,
        isLocal: true,
      })),
    ]);
  };

  const handleSendMessage = async () => {
    if (!inputValue.trim() && uploadedFiles.length === 0) {
      return;
    }

    if (!isAuthenticated) {
      console.error("User must be authenticated to send messages");
      return;
    }

    if (isSending) {
      return; // Prevent duplicate sends
    }

    setIsSending(true);
    setIsUploading(uploadedFiles.length > 0);

    try {
      const messageText = inputValue.trim() || "";
      const filesToUpload = [...uploadedFiles];

      // Clear input and files immediately
      setInputValue("");
      setUploadedFiles([]);

      // If this is the first message, create a chat first
      let chatId = currentChatId;
      if (!chatId) {
        const chatResponse = await chatAPI.createChat("New Chat");
        chatId = chatResponse.chat_uuid;
        setCurrentChatId(chatId);

        // Mark this chat as already loaded to prevent duplicate message loading
        loadedChatIdRef.current = chatId;

        // Navigate to the new chat URL
        navigate(`/chats/${chatId}`);

        // Refresh chat history in sidebar
        refreshChatHistory();
      }
      // Create a single message for text and/or files
      const messageContent =
        messageText ||
        (filesToUpload.length > 0
          ? `${FILE_ATTACHMENT_INDICATOR} ${filesToUpload
              .map((f) => f.name)
              .join(", ")}`
          : "");

      const messageResponse = await chatAPI.addMessage(
        chatId,
        messageContent,
        "user",
      );

      // Upload all files with this message_id
      const uploadedFileData = [];
      if (filesToUpload.length > 0) {
        for (const fileItem of filesToUpload) {
          const formData = new FormData();
          formData.append("file", fileItem.file);
          formData.append("chat_uuid", chatId);
          formData.append("message_id", messageResponse.id);

          try {
            const response = await fetch(`${API_SERVER_URL}/api/upload`, {
              method: "POST",
              body: formData,
              credentials: "include",
            });

            if (response.ok) {
              const data = await response.json();
              uploadedFileData.push({
                name: data.filename,
                url: `${API_SERVER_URL}${data.url}`,
                type: fileItem.fileType,
                size: data.size,
              });
            } else {
              setErrorNotification(`Failed to upload file: ${fileItem.name}`);
            }
          } catch (error) {
            setErrorNotification(
              `Error uploading file ${fileItem.name}: ${error.message}`,
            );
          }
        }
      }

      // Add the single message to UI with all files
      const newMessage = {
        id: messageResponse.id,
        text: messageResponse.content,
        sender: messageResponse.role === "user" ? "user" : "assistant",
        timestamp: messageResponse.created_at,
        files: uploadedFileData,
      };

      setMessages((prev) => [...prev, newMessage]);

      // Message was successfully sent to backend
      console.log("Message sent successfully");
    } catch (error) {
      console.error("Error sending message:", error);
      setErrorNotification(`Failed to send message: ${error.message}`);
    } finally {
      setIsSending(false);
      setIsUploading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div
      className={`flex flex-col h-screen w-full transition-all duration-300 px-4 md:px-0 ${
        isSidebarOpen ? "md:ml-32" : ""
      } pt-12`}
    >
      {/* Toast Notification */}
      <Toast
        message={errorNotification}
        type="error"
        onClose={() => setErrorNotification(null)}
        duration={5000}
      />

      {messages.length === 0 && !chatId && !shareId ? (
        /* Centered Input when no messages and no chatId */
        <div
          className={`flex-1 flex items-center justify-center py-4 ${
            theme === "dark" ? "bg-gray-900" : "bg-gray-50"
          }`}
        >
          <div className="w-full max-w-5xl mx-auto px-4">
            <TextBox
              theme={theme}
              textareaRef={textareaRef}
              inputValue={inputValue}
              handleKeyPress={handleKeyPress}
              setInputValue={setInputValue}
              isAuthenticated={isAuthenticated}
              handleSendMessage={handleSendMessage}
              handleFileSelect={handleFileSelect}
              uploadedFiles={uploadedFiles}
              setUploadedFiles={setUploadedFiles}
              isUploading={isUploading}
            />
          </div>
        </div>
      ) : (
        <>
          {/* Conversation Area - grows to fill space */}
          <div
            className={`flex-1 overflow-y-auto py-4 ${
              theme === "dark" ? "bg-gray-900" : "bg-gray-50"
            }`}
          >
            <div className="w-full max-w-5xl mx-auto space-y-4 px-4">
              {/* Display messages */}
              <ChatMessages
                messages={messages}
                isLoading={isLoadingMessages}
                error={loadError}
              />
            </div>
          </div>

          {/* Chat Input Area - fixed at bottom */}
          <div
            className={`py-4 ${
              theme === "dark" ? "bg-gray-900" : "bg-gray-50"
            }`}
          >
            <div className="w-full max-w-5xl mx-auto px-4">
              {shareId ? (
                <div
                  className={`p-4 rounded-lg border text-center ${
                    theme === "dark"
                      ? "bg-gray-800 border-gray-700"
                      : "bg-gray-100 border-gray-200"
                  }`}
                >
                  <p
                    className={`text-sm ${
                      theme === "dark" ? "text-gray-400" : "text-gray-600"
                    }`}
                  >
                    This is a shared read-only view.{" "}
                    <button
                      onClick={() => navigate("/")}
                      className="text-blue-500 hover:underline"
                    >
                      Create your own chat
                    </button>
                  </p>
                </div>
              ) : (
                <TextBox
                  theme={theme}
                  textareaRef={textareaRef}
                  inputValue={inputValue}
                  handleKeyPress={handleKeyPress}
                  setInputValue={setInputValue}
                  isAuthenticated={isAuthenticated}
                  handleSendMessage={handleSendMessage}
                  handleFileSelect={handleFileSelect}
                  uploadedFiles={uploadedFiles}
                  setUploadedFiles={setUploadedFiles}
                  isUploading={isUploading}
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatInterface;
