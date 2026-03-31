import React, { useState, useEffect, useRef, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPaperPlane,
  faFile,
  faImage,
  faXmark,
  faBrain,
  faCheckCircle,
  faExclamationTriangle,
  faChevronDown,
  faChevronUp,
  faShare,
  faCopy,
  faCheck,
} from "@fortawesome/free-solid-svg-icons";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  deductCreditsLocal,
  useNumCredits,
  createCheckoutSession,
  useUser,
} from "../../redux/UserSlice";
import { useDispatch, useSelector } from "react-redux";
import { setChatMessages, selectCachedMessages } from "../../redux/ChatSlice";
import FileUpload from "../../components/FileUpload";
import fetcher, { postFormData } from "../../http/RequestConfig";
import ThinkingIndicator from "../chatbot/ThinkingIndicator";
import {
  createUploadedDocumentMessages,
  formatChatMessages,
  normalizeSources,
  sortMessagesByTimestamp,
  updateMessageWithStreamData,
} from "../chatbot/messageUtils";
import { useChatbotApi } from "../useChatbotApi";

// Development-only debug logging helper
const isDev = process.env.NODE_ENV === "development";

const Chatbot = ({
  createNewChat,
  handleChatSelect,
  isGuestMode = false,
  isPrivate,
  onChatsChanged,
  onUploadComplete,
  selectedChatId,
  processMessagePath = "process-message-pdf",
  uploadPath = "ingest-pdf",
  retrieveMessagesPath = "retrieve-messages-from-chat",
  retrieveDocsPath = "retrieve-current-docs",
  enableChatNameInference = true,
  emptyStateTitle = "What can I help you with?",
  streamResponses = true,
}) => {
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const pollingStartedRef = useRef(false);
  const { id } = useParams();
  const dispatch = useDispatch();
  const cachedMessages = useSelector(selectCachedMessages(id));
  const location = useLocation();
  const {
    inferChatName: inferChatNameRequest,
    processChatMessage,
    retrieveCurrentDocs,
    retrieveMessages,
    uploadDocuments,
  } = useChatbotApi();
  const numCredits = useNumCredits();
  const user = useUser();
  const [chatNameGenerated, setChatNameGenerated] = useState(false);
  const [messages, setMessages] = useState([]);
  const [uploadButtonClicked, setUploadButtonClicked] = useState(false);
  const pollingTimeoutRef = useRef(null);

  // State for tracking expanded reasoning sections
  const [expandedReasoning, setExpandedReasoning] = useState({});
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [showFileUpload, setShowFileUpload] = useState(false);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);
  // Inline image attachments staged for the next chat message
  const [pendingAttachments, setPendingAttachments] = useState([]);
  const imageInputRef = useRef(null);
  const [showShareModal, setShowShareModal] = useState(false);
  const [shareUrl, setShareUrl] = useState("");
  const [shareLoading, setShareLoading] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);

  const shouldShowUpgradeModal = () => {
    return user && numCredits === 0 && messages.length > 0 && !showUpgradeModal; // Only if not already shown
  };

  const handleImageAttachmentPick = (e) => {
    const files = Array.from(e.target.files || []);
    const picked = files.map((file) => ({
      id: `${file.name}-${file.size}-${file.lastModified}`,
      file,
      previewUrl: URL.createObjectURL(file),
      name: file.name,
    }));
    setPendingAttachments((prev) => [...prev, ...picked]);
    // Reset input so the same file can be re-selected if removed then re-added
    e.target.value = "";
  };

  const removeAttachment = (id) => {
    setPendingAttachments((prev) => {
      const removed = prev.find((a) => a.id === id);
      if (removed) URL.revokeObjectURL(removed.previewUrl);
      return prev.filter((a) => a.id !== id);
    });
  };

  const handleFileSelect = (files) => {
    console.log("Files selected:", files);
    setSelectedFiles(Array.isArray(files) ? files : [files]);
  };

  const handleFileRemove = (removedFile) => {
    console.log("File removed:", removedFile);
    setSelectedFiles((prev) => prev.filter((f) => f.id !== removedFile.id));
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) {
      alert("Please select files to upload");
      return;
    }

    try {
      // Check if we have a chat ID, if not, create a new chat first
      let chatId = id || selectedChatId;

      if (!chatId) {
        // For guests, don't create a persistent chat or navigate
        if (!user) {
          alert("Please log in to upload files and create persistent chats.");
          return;
        }

        // Create a new chat first for authenticated users
        try {
          chatId = await createNewChat();
          // Navigate to the new chat
          navigate(`/chat/${chatId}`, { id: chatId });
        } catch (err) {
          console.error("Failed to create chat:", err);
          alert("Failed to create a new chat. Please try again.");
          return;
        }
      }

      // Create FormData for file upload to match backend API
      const formData = new FormData();

      // Add files as 'files[]' to match backend expectation
      selectedFiles.forEach((fileObj) => {
        formData.append("files[]", fileObj.file);
      });

      // Add required chat_id parameter for ingest-pdf endpoint
      formData.append("chat_id", chatId);

      // Upload files using your existing fetcher to ingest-pdf endpoint
      const result = await uploadDocuments(uploadPath, formData);
      if (result) {
        console.log("Upload successful:", result);

        // Add uploaded files to the state for display
        const uploadedFileInfo = selectedFiles.map((fileObj) => ({
          name: fileObj.name,
          size: fileObj.size,
          uploadTime: new Date().toISOString(),
        }));
        // Add a system message to show files were uploaded
        const systemMessage = {
          id: `upload-${Date.now()}`,
          chat_id: chatId,
          role: "system",
          content: `📎 Uploaded ${selectedFiles.length} file(s): ${selectedFiles
            .map((f) => f.name)
            .join(", ")}`,
          isFileUpload: true,
          uploadedFiles: uploadedFileInfo,
          timestamp: Date.now(), // Add timestamp for proper sorting
        };

        setMessages((prev) => [...prev, systemMessage]);

        // Close modal and reset state
        setShowFileUpload(false);
        setSelectedFiles([]);

        // Optionally trigger a refresh or update
        if (onUploadComplete) {
          onUploadComplete(result);
        }

        // Don't show alert since we're showing it in chat
        // alert(`Successfully uploaded ${selectedFiles.length} file(s) to chat`);
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert(error?.message || "Upload failed. Please check your connection and try again.");
    }
  };

  const inferChatName = useCallback(async (text, answer, chatId) => {
    const combinedText = `${text} ${answer}`;
    try {
      await inferChatNameRequest(combinedText, chatId);
      onChatsChanged?.();
    } catch (err) {
      console.error("Chat name inference failed", err);
    }
  }, [inferChatNameRequest, onChatsChanged]);

  const handleShare = async () => {
    const chatId = id || selectedChatId;
    if (!chatId) return;
    setShareLoading(true);
    setShowShareModal(true);
    try {
      const res = await fetcher(`generate-playbook/${chatId}`, { method: "GET" });
      const data = await res.json();
      const slug = data.url; // e.g. "/playbook/abc-123"
      const fullUrl = `${window.location.origin}${slug}`;
      setShareUrl(fullUrl);
    } catch (err) {
      console.error("Failed to generate share URL:", err);
      setShareUrl("");
    } finally {
      setShareLoading(false);
    }
  };

  const handleCopyShareUrl = () => {
    if (!shareUrl) return;
    navigator.clipboard.writeText(shareUrl).then(() => {
      setShareCopied(true);
      setTimeout(() => setShareCopied(false), 2000);
    });
  };

  const pollForMessages = useCallback((chatId, maxAttempts = 3) => {
    let attempts = 0;

    const poll = async () => {
      attempts++;
      try {
        const data = await retrieveMessages("retrieve-messages-from-chat", chatId, 0);
        if (data.messages && data.messages.length > 0) {
          const formatted = formatChatMessages(data.messages, chatId);
          setMessages(formatted);
          localStorage.removeItem(`pending-message-${chatId}`);
          pollingTimeoutRef.current = null;
          return;
        }

        if (attempts < maxAttempts) {
          pollingTimeoutRef.current = setTimeout(poll, 2000);
        } else {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.isThinking
                ? {
                    ...msg,
                    content:
                      "Sorry, the request is taking too long. Please try again.",
                    isThinking: false,
                  }
                : msg
            )
          );
        }
      } catch (err) {
        console.error("Polling error:", err);
        setMessages((prev) =>
          prev.map((msg) =>
            msg.isThinking
              ? {
                  ...msg,
                  content:
                    "Sorry, I couldn't connect to the server. Please check your connection.",
                  isThinking: false,
                }
              : msg
          )
        );
        localStorage.removeItem(`pending-message-${chatId}`);
      }
    };

    pollingTimeoutRef.current = setTimeout(poll, 2000);
  }, [retrieveMessages]);

  // Function to fetch uploaded documents for a chat and create system messages
  const fetchUploadedDocuments = useCallback(async (chatId) => {
    try {
      const result = await retrieveCurrentDocs(retrieveDocsPath, chatId);
      console.log("Backend doc_info response:", result.doc_info);
      if (result.doc_info && result.doc_info.length > 0) {
        return createUploadedDocumentMessages(result.doc_info, chatId);
      }
    } catch (error) {
      console.error("Error fetching uploaded documents:", error);
    }
    return [];
  }, [retrieveCurrentDocs, retrieveDocsPath]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    console.log(
      "handleSendMessage called for user:",
      user ? "authenticated" : "guest"
    );

    if (!message.trim() && pendingAttachments.length === 0) return;

    // For authenticated users, check credits and deduct them
    if (user) {
      // Check if user has credits
      if (numCredits === 0) {
        setShowUpgradeModal(true);
        return;
      }
      // Deduct credits for authenticated users
      await dispatch(deductCreditsLocal(1)).unwrap();
    }
    // For guests, we skip credit checks and allow them to chat

    const currentMessage = message.trim();
    const currentAttachments = pendingAttachments;
    setMessage("");
    setPendingAttachments([]);

    let targetChatId = id || selectedChatId;

    const isNewChat = !targetChatId;

    if (isNewChat) {
      try {
        // For guests, create a temporary chat experience without navigation
        if (!user) {
          console.log("Creating guest chat experience");
          // Create a temporary guest chat ID
          targetChatId = `guest-${Date.now()}`;

          const userMsg = {
            id: `user-${Date.now()}`,
            chat_id: targetChatId,
            role: "user",
            relevant_chunks: [],
            content: currentMessage,
            timestamp: Date.now(),
          };
          const thinkingMsg = {
            id: `thinking-${Date.now()}`,
            chat_id: targetChatId,
            role: "assistant",
            content: "",
            isThinking: true,
            reasoning: [],
            sources: [],
            timestamp: Date.now(),
          };

          console.log("Setting guest messages:", [userMsg, thinkingMsg]);
          setMessages([userMsg, thinkingMsg]);

          // Send to API for guest chat without creating a persistent chat
          try {
            console.log("Sending guest chat to API");
            await sendToAPI(userMsg, null, thinkingMsg.id);
            // For now, let's provide a mock response for guests to avoid API issues
            // TODO: Update backend to support guest mode properly
            // setTimeout(() => {
            //   setMessages((prev) =>
            //     prev.map((msg) =>
            //       msg.id === thinkingMsg.id
            //         ? {
            //             ...msg,
            //             content:
            //               "Hello! I'm currently in guest mode. To access full AI document analysis features, please log in or create an account. For now, I can provide basic responses, but full functionality requires authentication.",
            //             isThinking: false,
            //           }
            //         : msg
            //     )
            //   );
            // }, 1000);

            // Uncomment this when backend supports guest mode:
            // await sendToAPI(currentMessage, targetChatId, thinkingMsg.id);
            console.log("Guest chat API call completed");
          } catch (error) {
            console.error("Guest chat API error:", error);
            // Update thinking message to show error
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === thinkingMsg.id
                  ? {
                      ...msg,
                      content:
                        "Sorry, I'm having trouble connecting. Please try again.",
                      isThinking: false,
                    }
                  : msg
              )
            );
          }
          console.log("Guest chat flow completed, returning");
          return;
        }
        if (user) {
          // For authenticated users, create a real chat and navigate
          targetChatId = await createNewChat();
          navigate(`/chat/${targetChatId}`, {
            state: { message: currentMessage },
          });
        }
        localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);

        const userMsg = {
          id: `user-${Date.now()}`,
          chat_id: targetChatId,
          role: "user",
          relevant_chunks: [],
          content: currentMessage,
          timestamp: Date.now(),
        };
        const thinkingMsg = {
          id: `thinking-${Date.now()}`,
          chat_id: targetChatId,
          role: "assistant",
          content: "",
          isThinking: true,
          reasoning: [],
          sources: [],
          timestamp: Date.now(),
        };

        setMessages([userMsg, thinkingMsg]);

        if (!pollingStartedRef.current) {
          pollForMessages(targetChatId);
          pollingStartedRef.current = true;
        }

        return;
      } catch (err) {
        console.error("Failed to create chat:", err);
        setMessage(currentMessage);
        return;
      }
    }

    // For existing chat (both authenticated and guest)
    const thinkingId = `thinking-${Date.now()}`;
    const now = Date.now();
    setMessages((prev) => [
      ...prev,
      {
        id: `user-${now}`,
        chat_id: targetChatId,
        role: "user",
        content: currentMessage,
        attachments: currentAttachments.map((a) => ({
          previewUrl: a.previewUrl,
          name: a.name,
        })),
        timestamp: now,
      },
      {
        id: thinkingId,
        chat_id: targetChatId,
        role: "assistant",
        content: "",
        isThinking: true,
        reasoning: [],
        sources: [],
        timestamp: now + 1,
      },
    ]);

    // Only store in localStorage for authenticated user chats
    if (user) {
      localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);
    }
    await sendToAPI(currentMessage, targetChatId, thinkingId, currentAttachments);
  };

  const handleSSEStreamingResponse = useCallback(async (
    response,
    thinkingId,
    originalText,
    chatId
  ) => {
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.trim() === "") continue;

          if (line.startsWith("data: ")) {
            const dataContent = line.slice(6);

            if (dataContent === "[DONE]") {
              console.log("✅ Stream completed");
              // Mark streaming as complete and ensure final state
              setMessages((prev) =>
                prev.map((msg) =>
                  msg.id === thinkingId
                    ? {
                        ...msg,
                        isThinking: false,
                        currentStep: null,
                      }
                    : msg
                )
              );
              break;
            }

            try {
              const eventData = JSON.parse(dataContent);

              // Update the message directly in the messages array
              setMessages((prev) => {
                const updated = prev.map((msg) => {
                  if (msg.id === thinkingId) {
                    const updatedMsg = updateMessageWithStreamData(
                      msg,
                      eventData
                    );
                    // Force re-render by ensuring object reference changes
                    return { ...updatedMsg };
                  }
                  return msg;
                });
                return [...updated]; // Force array reference change
              });

              // Generate chat name when we get the final answer (skip for guest chats)
              const isGuestChat =
                typeof chatId === "string" && chatId.startsWith("guest-");
              if (
                (eventData.type === "complete" ||
                  eventData.type === "step-complete") &&
                eventData.answer &&
                !chatNameGenerated &&
                !isGuestChat &&
                enableChatNameInference
              ) {
                await inferChatName(originalText, eventData.answer, chatId);
                setChatNameGenerated(true);
                onChatsChanged?.();
              }

              // Force final state update for completion events
              if (
                eventData.type === "complete" ||
                eventData.type === "step-complete"
              ) {
                const normalizedSources = normalizeSources(eventData.sources);
                setTimeout(() => {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === thinkingId
                        ? {
                            ...msg,
                            isThinking: false,
                            currentStep: null,
                            content: eventData.answer || msg.content,
                            sources: normalizedSources.length
                              ? normalizedSources
                              : msg.sources || [],
                            charts: [
                              ...(msg.charts || []),
                              ...(eventData.charts || []),
                            ],
                          }
                        : msg
                    )
                  );
                }, 100); // Small delay to ensure all updates are processed
              }
            } catch (e) {
              console.error("Error parsing streaming data:", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Streaming error:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingId
            ? {
                ...msg,
                content: "Sorry, there was an error processing your request.",
                isThinking: false,
              }
            : msg
        )
      );
    }
  }, [chatNameGenerated, enableChatNameInference, inferChatName, onChatsChanged]);

  const sendToAPI = useCallback(async (text, chatId, thinkingId, attachments = []) => {
    try {
      const isGuestChat =
        (typeof chatId === "string" && chatId.startsWith("guest-")) ||
        (!user && chatId === null);

      if (isDev) {
        console.log("sendToAPI called with:", {
          text,
          chatId,
          isGuestChat,
          user: !!user,
          attachments: attachments.length,
        });
      }

      let res;
      if (attachments.length > 0) {
        // Use multipart/form-data so image files travel alongside the message
        const form = new FormData();
        form.append("message", text);
        form.append("chat_id", isGuestChat ? "" : String(Number(chatId)));
        form.append("model_type", String(isPrivate));
        form.append("model_key", "");
        form.append("is_guest", isGuestChat ? "true" : "false");
        attachments.forEach((a) => form.append("attachments[]", a.file));
        res = await postFormData("process-message-pdf", form, { isGuest: isGuestChat });
      } else {
        res = await fetcher("process-message-pdf", {
          method: "POST",
          isGuest: isGuestChat,
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: text,
            chat_id: isGuestChat ? null : Number(chatId),
            model_type: isPrivate,
            model_key: "",
            is_guest: isGuestChat,
          }),
        });
      }

      // Revoke object URLs now the request is away
      attachments.forEach((a) => URL.revokeObjectURL(a.previewUrl));

      if (isDev) {
        console.log("API response status:", res.status);
      }
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      if (streamResponses) {
        await handleSSEStreamingResponse(res, thinkingId, text, chatId);
      } else {
        const data = await res.json();
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === thinkingId
              ? {
                  ...msg,
                  content:
                    data.answer ||
                    "Sorry, I couldn't generate a response. Please try again.",
                  isThinking: false,
                  sources: data.sources || [],
                  reasoning: data.reasoning || [],
                }
              : msg
          )
        );
      }

      if (!isGuestChat) {
        localStorage.removeItem(`pending-message-${chatId}`);
      }
      if (isDev) {
        console.log("sendToAPI completed successfully");
      }
    } catch (err) {
      console.error("Message send error:", err);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === thinkingId
            ? {
                ...msg,
                content:
                  "Sorry, I couldn't connect to the server. Please try again.",
                isThinking: false,
              }
            : msg
        )
      );
    }
  }, [handleSSEStreamingResponse, isPrivate, processChatMessage, processMessagePath, streamResponses, user]);

  // Function to toggle reasoning expansion
  const toggleReasoningExpansion = (messageId) => {
    setExpandedReasoning((prev) => ({
      ...prev,
      [messageId]: !prev[messageId],
    }));
  };

  useEffect(() => {
    if (pollingTimeoutRef.current) {
      clearTimeout(pollingTimeoutRef.current);
      pollingTimeoutRef.current = null;
    }

    pollingStartedRef.current = false;

    const activeChatId = id || selectedChatId;

    if (activeChatId) {
      const loadChat = async () => {
        if (handleChatSelect && activeChatId !== selectedChatId) {
          handleChatSelect(activeChatId);
        }

        // Seed from Redux cache immediately so the user sees messages
        // without a loading flash while the network request is in-flight.
        if (cachedMessages?.length) {
          setMessages(cachedMessages);
        }

        try {
          const data = await retrieveMessages(retrieveMessagesPath, activeChatId, 0);

          console.log("res", data);
          setChatNameGenerated(true);

          if (!data.messages?.length) {
            const pending =
              location.state?.message ||
              localStorage.getItem(`pending-message-${activeChatId}`);
            if (pending) {
              console.log(
                "[handleLoadChat] Loading pending message after new chat creation:",
                pending
              );
              const userMsg = {
                id: "user-content",
                chat_id: activeChatId,
                role: "user",
                content: pending,
                timestamp: Date.now(),
              };
              const thinkingMsg = {
                id: `thinking-${Date.now()}`,
                chat_id: activeChatId,
                role: "assistant",
                content: "",
                isThinking: true,
                reasoning: [],
                sources: [],
                timestamp: Date.now() + 1,
              };
              setMessages([userMsg, thinkingMsg]);
              if (location.state?.message) {
                localStorage.setItem(
                  `pending-message-${activeChatId}`,
                  location.state.message
                );
              }
              await sendToAPI(pending, activeChatId, thinkingMsg.id);
              return;
            }

            setMessages([]);
            return;
          }

          localStorage.removeItem(`pending-message-${activeChatId}`);
          const formatted = formatChatMessages(data.messages, activeChatId);

          const fileSystemMessages = await fetchUploadedDocuments(activeChatId);
          const sorted = sortMessagesByTimestamp([...formatted, ...fileSystemMessages]);
          setMessages(sorted);
          // Update the Redux cache so the next visit to this chat is instant.
          dispatch(setChatMessages({ chatId: activeChatId, messages: sorted }));
        } catch (err) {
          console.error("Failed to load chat:", err);
        }
      };

      loadChat();
    } else {
      setMessages([]);
      setChatNameGenerated(false);
    }

    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
  }, [
    id,
    location.state?.message,
    fetchUploadedDocuments,
    retrieveMessages,
    retrieveMessagesPath,
    selectedChatId,
    handleChatSelect,
    sendToAPI,
    cachedMessages,
    dispatch,
  ]);

  const handleInputKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (message.trim() !== "") {
        handleSendMessage(e);
      }
    }
  };

  return (
    <div
      className={`h-full bg-anoteblack-800 w-full ${
        messages.length !== 0 && "pt-16"
      } flex flex-col`}
    >
      <div
        ref={(ref) =>
          ref && ref.scrollTo({ top: ref.scrollHeight, behavior: "smooth" })
        }
        className={`h-full rounded overflow-auto ${
          messages.length > 0 ? "block" : "hidden"
        } flex justify-center`}
      >
        <div className="py-3 flex-col mt-0 px-4 flex gap-3 w-full">
          <div className="px-4 md:px-8 lg:px-16 xl:px-32">
            {messages.map((msg, index) => (
              <div
                key={`${msg.chat_id}-${msg.id || index}`}
                className={`flex items-start gap-4 mb-4 ${
                  msg.role === "user"
                    ? "justify-end"
                    : msg.role === "system"
                    ? "justify-center"
                    : "justify-start"
                }`}
              >
                {/* System messages (file uploads) */}
                {msg.role === "system" && msg.isFileUpload ? (
                  <div className="w-full max-w-md mx-auto">
                    <div className="bg-green-900/30 border border-green-600/50 rounded-xl p-3 text-center">
                      <div className="flex items-center justify-center gap-2 text-green-400 text-sm">
                        <FontAwesomeIcon icon={faFile} />
                        <span className="font-medium">{msg.content}</span>
                      </div>
                      {msg.uploadedFiles && msg.uploadedFiles.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {msg.uploadedFiles.map((file, idx) => (
                            <div
                              key={idx}
                              className="text-xs text-green-300 flex items-center justify-center gap-2"
                            >
                              <span>{file.name}</span>
                              <span className="text-green-500">
                                ({(file.size / 1024).toFixed(1)} KB)
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ) : (
                  /* Regular messages (user/assistant) */
                  <div
                    className={`space-y-3 ${
                      msg.role === "assistant"
                        ? "w-full md:w-5/6 lg:w-3/4 xl:w-2/3"
                        : ""
                    }`}
                  >
                    {/* Reasoning Box - Shows during streaming and after completion */}
                    {msg.role === "assistant" &&
                      (msg.reasoning?.length > 0 || msg.isThinking) && (
                        <div className="bg-[#0f1419] border border-[#2e3a4c] rounded-xl p-4 mb-3">
                          <button
                            onClick={() => toggleReasoningExpansion(msg.id)}
                            className="flex items-center justify-between w-full text-left text-xs text-gray-400 hover:text-gray-200 transition-colors"
                          >
                            <div className="flex items-center gap-2">
                              <FontAwesomeIcon icon={faBrain} />
                              <span>
                                {msg.isThinking
                                  ? "AI Reasoning (Live)"
                                  : `AI Reasoning Steps (${
                                      msg.reasoning?.length || 0
                                    })`}
                              </span>
                            </div>
                            <FontAwesomeIcon
                              icon={
                                expandedReasoning[msg.id]
                                  ? faChevronUp
                                  : faChevronDown
                              }
                              className="text-xs"
                            />
                          </button>

                          {expandedReasoning[msg.id] && (
                            <div className="mt-3 space-y-2 animate-fade-in">
                              {/* Show current step during thinking */}
                              {msg.isThinking && msg.currentStep && (
                                <div className="border-l-2 border-yellow-400 bg-yellow-950/20 pl-3 py-2 mb-2">
                                  <ThinkingIndicator step={msg.currentStep} />
                                </div>
                              )}

                              {/* Show completed reasoning steps */}
                              {msg.reasoning?.map((step, idx) => (
                                <ThinkingIndicator
                                  key={step.id || idx}
                                  step={step}
                                />
                              ))}
                            </div>
                          )}
                        </div>
                      )}

                    {/* Main message content */}
                    <div
                      className={`rounded-2xl p-4 shadow-lg transition-all ${
                        msg.role === "user"
                          ? "bg-[#222d3c]  border border-[#2e3a4c] text-white ml-auto rounded-br-none"
                          : "bg-[#181f29] text-white border border-[#2e3a4c] rounded-bl-none"
                      }`}
                    >
                      {/* Assistant Thinking Animation */}
                      {msg.isThinking ? (
                        <div className="space-y-3">
                          <div className="flex items-center gap-2">
                            <div className="flex space-x-1">
                              <div className="w-2 h-2 bg-[#defe47] rounded-full animate-pulse"></div>
                              <div
                                className="w-2 h-2 bg-[#defe47] rounded-full animate-pulse"
                                style={{ animationDelay: "0.2s" }}
                              ></div>
                              <div
                                className="w-2 h-2 bg-[#defe47] rounded-full animate-pulse"
                                style={{ animationDelay: "0.4s" }}
                              ></div>
                            </div>
                            <span className="text-sm text-gray-400">
                              AI is thinking...
                            </span>
                          </div>

                          {/* Show partial content if available during streaming */}
                          {msg.content && (
                            <div className="mt-3">
                              <p className="whitespace-pre-wrap leading-relaxed text-sm">
                                {msg.content}
                              </p>
                            </div>
                          )}
                          {/* Show charts as they arrive during streaming */}
                          {msg.charts && msg.charts.length > 0 && (
                            <div className="mt-3 space-y-2">
                              {msg.charts.map((chart, idx) => (
                                <div key={idx} className="rounded-lg overflow-hidden border border-[#2e3a4c]">
                                  <img
                                    src={`data:image/png;base64,${chart.image_data}`}
                                    alt={chart.title || "Chart"}
                                    className="w-full max-w-lg"
                                  />
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div>
                          {/* Image thumbnails for user messages with attachments */}
                          {msg.role === "user" && msg.attachments?.length > 0 && (
                            <div className="flex flex-wrap gap-2 mb-2">
                              {msg.attachments.map((att, i) => (
                                <img
                                  key={i}
                                  src={att.previewUrl}
                                  alt={att.name}
                                  className="max-h-48 max-w-xs rounded-lg object-cover border border-gray-600"
                                />
                              ))}
                            </div>
                          )}
                          {/* Main response content */}
                          {msg.content && (
                            <p className="whitespace-pre-wrap leading-relaxed text-sm">
                              {msg.content}
                            </p>
                          )}
                          {/* Inline charts */}
                          {msg.charts && msg.charts.length > 0 && (
                            <div className="mt-4 space-y-3">
                              {msg.charts.map((chart, idx) => (
                                <div key={idx} className="rounded-lg overflow-hidden border border-[#2e3a4c]">
                                  {chart.title && (
                                    <div className="px-3 py-1 bg-[#0f1419] text-xs text-gray-400 font-medium">
                                      {chart.title}
                                    </div>
                                  )}
                                  <img
                                    src={`data:image/png;base64,${chart.image_data}`}
                                    alt={chart.title || "Chart"}
                                    className="w-full max-w-lg"
                                  />
                                </div>
                              ))}
                            </div>
                          )}
                          {msg.role === "assistant" &&
                            !msg.isThinking &&
                            msg.sources?.length > 0 && (
                              <div className="mt-4 border-t border-[#2e3a4c] pt-3">
                                <div className="text-xs font-semibold uppercase tracking-wide text-[#defe47] mb-2">
                                  Grounded Sources
                                </div>
                                <div className="space-y-2">
                                  {msg.sources.map((source, sourceIndex) => (
                                    <div
                                      key={source.id || sourceIndex}
                                      className="rounded-lg border border-[#2e3a4c] bg-[#0f1419] p-3"
                                    >
                                      <div className="flex items-center justify-between gap-2 text-xs text-gray-300">
                                        <span className="font-medium text-white">
                                          {source.document_name}
                                        </span>
                                        <span className="text-gray-400">
                                          {source.page_number != null
                                            ? `Page ${source.page_number}`
                                            : "Document evidence"}
                                        </span>
                                      </div>
                                      <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-gray-300">
                                        {source.chunk_text}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            )}
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div
        className={`flex-shrink-0 borderrounded-xl ${
          messages.length === 0
            ? "flex-1 flex items-center gap-2 flex-col justify-center"
            : ""
        }`}
      >
        {/* Welcome message */}
        {messages.length === 0 && (
          <div className="w-full text-white animate-typing overflow-hidden whitespace-nowrap flex items-center justify-center font-bold text-2xl mb-4">
            {emptyStateTitle}
          </div>
        )}


        {/* Input form */}
        <div className="flex w-full justify-center mb-4 px-4">
          <div className="flex flex-col gap-1 focus-within:ring-slate-600 focus-within:ring-2 border-gray-600 p-2 rounded-xl bg-sidebar w-full max-w-4xl">
            {/* Pending image attachment previews */}
            {pendingAttachments.length > 0 && (
              <div className="flex flex-wrap gap-2 px-2 pt-1">
                {pendingAttachments.map((attachment) => (
                  <div key={attachment.id} className="relative group">
                    <img
                      src={attachment.previewUrl}
                      alt={attachment.name}
                      className="h-16 w-16 object-cover rounded-lg border border-gray-600"
                    />
                    <button
                      type="button"
                      onClick={() => removeAttachment(attachment.id)}
                      className="absolute -top-1.5 -right-1.5 bg-gray-700 hover:bg-red-600 text-white rounded-full w-5 h-5 flex items-center justify-center transition-colors"
                      title="Remove image"
                    >
                      <FontAwesomeIcon icon={faXmark} className="text-xs" />
                    </button>
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center gap-1">
              {/* Hidden image file input */}
              <input
                ref={imageInputRef}
                type="file"
                accept="image/jpeg,image/png,image/gif,image/webp,image/bmp"
                multiple
                onChange={handleImageAttachmentPick}
                className="hidden"
              />

              {/* Left side - Document upload button */}
              <button
                type="button"
                onClick={() => {
                  setShowFileUpload(true);
                  setUploadButtonClicked(true);
                  setTimeout(() => setUploadButtonClicked(false), 1000);
                }}
                disabled={!user ? false : numCredits === 0}
                className={`flex items-center justify-center w-12 h-12 rounded-lg transition-colors flex-shrink-0 ${
                  uploadButtonClicked
                    ? "bg-gray-600 text-white"
                    : "bg-gray-600 hover:bg-gray-500 text-white"
                }`}
                title={!id ? "Please select or create a chat first" : "Upload documents"}
              >
                <FontAwesomeIcon icon={faFile} className="text-lg" />
              </button>

              {/* Image attach button */}
              <button
                type="button"
                onClick={() => imageInputRef.current?.click()}
                disabled={messages.some((msg) => msg.isThinking)}
                className="flex items-center justify-center w-12 h-12 rounded-lg transition-colors flex-shrink-0 bg-gray-600 hover:bg-gray-500 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                title="Attach images"
              >
                <FontAwesomeIcon icon={faImage} className="text-lg" />
              </button>

              {/* Share button — only for authenticated users with an active chat */}
              {user && (id || selectedChatId) && messages.length > 0 && (
                <button
                  type="button"
                  onClick={handleShare}
                  className="flex items-center justify-center w-12 h-12 rounded-lg transition-colors flex-shrink-0 bg-gray-600 hover:bg-gray-500 text-white"
                  title="Share this chat as a playbook"
                >
                  <FontAwesomeIcon icon={faShare} className="text-lg" />
                </button>
              )}

              {/* Center - Input */}
              <div className="flex-1">
                <div className="relative flex items-center rounded-lg focus-within:border-accent focus-within:ring-0 transition-all duration-200">
                  <textarea
                    className="w-full border-none disabled:cursor-not-allowed resize-none text-base px-4 py-3 focus:ring-0 focus:outline-none text-white placeholder:text-gray-400 bg-transparent rounded-lg"
                    rows={1}
                    placeholder={
                      !user
                        ? "Ask your question (guest mode)"
                        : pendingAttachments.length > 0
                        ? "Ask about your image..."
                        : "Ask your document a question"
                    }
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    ref={inputRef}
                    onKeyDown={handleInputKeyDown}
                    disabled={messages.some((msg) => msg.isThinking)}
                  />
                </div>
              </div>

              {/* Right side - Send button */}
              <button
                type="button"
                onClick={handleSendMessage}
                disabled={
                  ((!message || message.trim() === "") && pendingAttachments.length === 0) ||
                  messages.some((msg) => msg.isThinking)
                }
                className={`flex items-center justify-center w-12 h-12 rounded-lg transition-colors flex-shrink-0 ${
                  ((!message || message.trim() === "") && pendingAttachments.length === 0) ||
                  messages.some((msg) => msg.isThinking)
                    ? "bg-gray-600 text-gray-400 cursor-not-allowed"
                    : "bg-gray-600 hover:bg-gray-500 text-white"
                }`}
              >
                <FontAwesomeIcon icon={faPaperPlane} className="text-lg" />
              </button>
            </div>
          </div>
        </div>
      </div>
      {/* Share / Playbook Modal */}
      {showShareModal && (
        <div
          className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50 p-4"
          onClick={(e) => { if (e.target === e.currentTarget) setShowShareModal(false); }}
          onKeyDown={(e) => { if (e.key === "Escape") setShowShareModal(false); }}
        >
          <div className="bg-gray-800 rounded-xl p-6 w-full max-w-lg shadow-2xl">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white flex items-center gap-2">
                <FontAwesomeIcon icon={faShare} className="text-[#defe47]" />
                Share Playbook
              </h2>
              <button
                onClick={() => setShowShareModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {shareLoading ? (
              <div className="flex items-center justify-center py-8 text-gray-400">
                <div className="w-5 h-5 border-2 border-gray-400 border-t-[#defe47] rounded-full animate-spin mr-3" />
                Generating shareable link…
              </div>
            ) : shareUrl ? (
              <div className="space-y-4">
                <p className="text-sm text-gray-300">
                  Anyone with this link can view a read-only snapshot of this chat
                  and import it into their own workspace.
                </p>
                <div className="flex items-center gap-2 bg-gray-900 border border-gray-600 rounded-lg p-3">
                  <span className="flex-1 text-sm text-gray-200 truncate select-all">{shareUrl}</span>
                  <button
                    onClick={handleCopyShareUrl}
                    className="flex items-center gap-1 px-3 py-1.5 bg-[#defe47] text-black text-sm font-medium rounded-md hover:bg-yellow-300 transition-colors flex-shrink-0"
                  >
                    <FontAwesomeIcon icon={shareCopied ? faCheck : faCopy} className="text-xs" />
                    {shareCopied ? "Copied!" : "Copy"}
                  </button>
                </div>
              </div>
            ) : (
              <p className="text-sm text-red-400 py-4 text-center">
                Failed to generate share link. Please try again.
              </p>
            )}
          </div>
        </div>
      )}

      {/* File Upload Modal */}
      {showFileUpload && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowFileUpload(false);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setShowFileUpload(false);
            }
          }}
        >
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">Upload Files</h2>
              <button
                onClick={() => setShowFileUpload(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <FileUpload
              onFileSelect={handleFileSelect}
              onFileRemove={handleFileRemove}
              acceptedFileTypes=".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls"
              maxFileSize={10 * 1024 * 1024} // 10MB
              multiple={true}
              placeholder="Upload files to analyze with AI"
              className="mb-4"
            />

            {selectedFiles.length > 0 && (
              <div className="flex justify-end space-x-3 mt-4">
                <button
                  onClick={() => {
                    setSelectedFiles([]);
                    setShowFileUpload(false);
                  }}
                  className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={handleUpload}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  Upload {selectedFiles.length} file
                  {selectedFiles.length > 1 ? "s" : ""}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Upgrade Modal - Only show for authenticated users */}
      {shouldShowUpgradeModal() && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) {
              setShowUpgradeModal(false);
            }
          }}
          onKeyDown={(e) => {
            if (e.key === "Escape") {
              setShowUpgradeModal(false);
            }
          }}
        >
          <div className="bg-gray-800 rounded-lg p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-white">
                Upgrade Your Plan
              </h2>
              <button
                onClick={() => setShowUpgradeModal(false)}
                className="text-gray-400 hover:text-white transition-colors"
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="text-center mb-6">
              <FontAwesomeIcon
                icon={faExclamationTriangle}
                className="text-red-400 text-4xl mb-3"
              />
              <h3 className="text-lg font-medium text-white mb-2">
                Choose Your Plan
              </h3>
              <p className="text-gray-300 text-sm">
                Upgrade to continue using our AI-powered financial analysis
                tools with enhanced features and priority support.
              </p>
            </div>

            {/* Pricing Options */}
            <div className="space-y-4 mb-6">
              {/* Basic Plan */}
              <div className="border border-gray-600 rounded-lg p-4 hover:border-blue-400 transition-colors">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-white font-medium">Basic Plan</h4>
                  <span className="text-blue-400 font-bold">$19/month</span>
                </div>
                <p className="text-gray-300 text-sm mb-2">
                  200 credits per month • Perfect for individuals
                </p>
                <ul className="text-xs text-gray-400 mb-3 space-y-1">
                  <li>• Advanced AI document analysis</li>
                  <li>• PDF, DOCX, TXT file support</li>
                  <li>• Basic chat history</li>
                </ul>
                <button
                  onClick={async () => {
                    console.log("Button clicked - attempting checkout...");
                    try {
                      console.log(
                        "Dispatching createCheckoutSession with product_hash: privategpt1"
                      );
                      const response = await dispatch(
                        createCheckoutSession({ product_hash: "privategpt1" })
                      );
                      console.log("Checkout response:", response);
                      const checkoutUrl = response.payload;
                      console.log("Checkout URL:", checkoutUrl);

                      if (checkoutUrl) {
                        window.open(checkoutUrl, "_blank");
                        setShowUpgradeModal(false);
                      } else {
                        console.error("No checkout URL received");
                        alert("Failed to get checkout URL. Please try again.");
                      }
                    } catch (error) {
                      console.error("Error creating checkout session:", error);

                      // Check if it's a user not found error
                      if (
                        error?.payload?.status === 404 ||
                        error?.response?.status === 404
                      ) {
                        alert(
                          "User account not found. Please ensure you're logged in and try again."
                        );
                      } else if (
                        error?.payload?.status === 401 ||
                        error?.response?.status === 401
                      ) {
                        alert(
                          "Authentication failed. Please log in again and try again."
                        );
                      } else {
                        alert(
                          "Failed to initiate checkout. Please try again or contact support."
                        );
                      }
                    }
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Select Basic
                </button>
              </div>

              {/* Standard Plan */}
              <div className="border border-blue-400 rounded-lg p-4 bg-blue-600/10">
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-2">
                    <h4 className="text-white font-medium">Standard Plan</h4>
                    <span className="bg-blue-600 text-white text-xs px-2 py-1 rounded-full">
                      Popular
                    </span>
                  </div>
                  <span className="text-blue-400 font-bold">$39/month</span>
                </div>
                <p className="text-gray-300 text-sm mb-2">
                  500 credits per month • Great for small teams
                </p>
                <ul className="text-xs text-gray-400 mb-3 space-y-1">
                  <li>• Everything in Basic</li>
                  <li>• Priority processing speed</li>
                  <li>• Advanced export options</li>
                  <li>• Email support</li>
                </ul>
                <button
                  onClick={async () => {
                    console.log(
                      "Standard plan button clicked - attempting checkout..."
                    );
                    try {
                      console.log(
                        "Dispatching createCheckoutSession with product_hash: privategpt2"
                      );
                      const response = await dispatch(
                        createCheckoutSession({ product_hash: "privategpt2" })
                      );
                      console.log("Checkout response:", response);
                      const checkoutUrl = response.payload;
                      console.log("Checkout URL:", checkoutUrl);

                      if (checkoutUrl) {
                        window.open(checkoutUrl, "_blank");
                        setShowUpgradeModal(false);
                      } else {
                        console.error("No checkout URL received");
                        alert("Failed to get checkout URL. Please try again.");
                      }
                    } catch (error) {
                      console.error("Error creating checkout session:", error);

                      // Check if it's a user not found error
                      if (
                        error?.payload?.status === 404 ||
                        error?.response?.status === 404
                      ) {
                        alert(
                          "User account not found. Please ensure you're logged in and try again."
                        );
                      } else if (
                        error?.payload?.status === 401 ||
                        error?.response?.status === 401
                      ) {
                        alert(
                          "Authentication failed. Please log in again and try again."
                        );
                      } else {
                        alert(
                          "Failed to initiate checkout. Please try again or contact support."
                        );
                      }
                    }
                  }}
                  className="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Select Standard
                </button>
              </div>

              {/* Premium Plan */}
              <div className="border border-gray-600 rounded-lg p-4 hover:border-purple-400 transition-colors">
                <div className="flex justify-between items-center mb-2">
                  <h4 className="text-white font-medium">Premium Plan</h4>
                  <span className="text-purple-400 font-bold">$79/month</span>
                </div>
                <p className="text-gray-300 text-sm mb-2">
                  1,500 credits per month • Best for enterprises
                </p>
                <ul className="text-xs text-gray-400 mb-3 space-y-1">
                  <li>• Everything in Standard</li>
                  <li>• Unlimited file uploads</li>
                  <li>• Custom AI model training</li>
                  <li>• Priority support & phone calls</li>
                  <li>• Advanced analytics dashboard</li>
                </ul>
                <button
                  onClick={async () => {
                    console.log(
                      "Premium plan button clicked - attempting checkout..."
                    );
                    try {
                      console.log(
                        "Dispatching createCheckoutSession with product_hash: privategpt3"
                      );
                      const response = await dispatch(
                        createCheckoutSession({ product_hash: "privategpt3" })
                      );
                      console.log("Checkout response:", response);
                      const checkoutUrl = response.payload;
                      console.log("Checkout URL:", checkoutUrl);

                      if (checkoutUrl) {
                        window.open(checkoutUrl, "_blank");
                        setShowUpgradeModal(false);
                      } else {
                        console.error("No checkout URL received");
                        alert("Failed to get checkout URL. Please try again.");
                      }
                    } catch (error) {
                      console.error("Error creating checkout session:", error);

                      // Check if it's a user not found error
                      if (
                        error?.payload?.status === 404 ||
                        error?.response?.status === 404
                      ) {
                        alert(
                          "User account not found. Please ensure you're logged in and try again."
                        );
                      } else if (
                        error?.payload?.status === 401 ||
                        error?.response?.status === 401
                      ) {
                        alert(
                          "Authentication failed. Please log in again and try again."
                        );
                      } else {
                        alert(
                          "Failed to initiate checkout. Please try again or contact support."
                        );
                      }
                    }
                  }}
                  className="w-full bg-purple-600 hover:bg-purple-700 text-white font-medium py-2 px-4 rounded-lg transition-colors"
                >
                  Select Premium
                </button>
              </div>
            </div>

            <div className="space-y-3">
              <div className="text-center">
                <p className="text-xs text-gray-400 mb-2">
                  <span className="inline-flex items-center gap-1">
                    <FontAwesomeIcon
                      icon={faCheckCircle}
                      className="text-green-400"
                    />
                    30-day money-back guarantee • Cancel anytime
                  </span>
                </p>
              </div>
              <button
                onClick={() => setShowUpgradeModal(false)}
                className="w-full bg-gray-600 hover:bg-gray-700 text-white font-medium py-3 px-4 rounded-lg transition-colors"
              >
                Maybe Later
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Chatbot;
