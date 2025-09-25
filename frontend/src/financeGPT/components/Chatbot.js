import React, { useState, useEffect, useRef, useCallback } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faPaperPlane,
  faFile,
  faBrain,
  faSearch,
  faCog,
  faCheckCircle,
  faExclamationTriangle,
  faChevronDown,
  faChevronUp,
  faArrowRight,
  faInfoCircle,
  faSitemap,
  faLightbulb,
} from "@fortawesome/free-solid-svg-icons";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import {
  deductCreditsLocal,
  useNumCredits,
  createCheckoutSession,
  useUser,
} from "../../redux/UserSlice";
import { useDispatch } from "react-redux";
import FileUpload from "../../components/FileUpload";
import fetcher from "../../http/RequestConfig";

// Development-only debug logging helper
const isDev = process.env.NODE_ENV === "development";

const Chatbot = (props) => {
  const [message, setMessage] = useState("");
  const inputRef = useRef(null);
  const navigate = useNavigate();
  const pollingStartedRef = useRef(false);
  const { id } = useParams();
  const dispatch = useDispatch();
  const location = useLocation();
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
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [showUpgradeModal, setShowUpgradeModal] = useState(false);

  const shouldShowUpgradeModal = () => {
    return user && numCredits === 0 && messages.length > 0 && !showUpgradeModal; // Only if not already shown
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
      let chatId = id || props.selectedChatId;

      if (!chatId) {
        // For guests, don't create a persistent chat or navigate
        if (!user) {
          alert("Please log in to upload files and create persistent chats.");
          return;
        }

        // Create a new chat first for authenticated users
        try {
          chatId = await props.createNewChat();
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
      const response = await fetcher("ingest-pdf", {
        method: "POST",
        body: formData,
        // Don't set Content-Type header for FormData, let browser set it
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Upload successful:", result);

        // Add uploaded files to the state for display
        const uploadedFileInfo = selectedFiles.map((fileObj) => ({
          name: fileObj.name,
          size: fileObj.size,
          uploadTime: new Date().toISOString(),
        }));
        setUploadedFiles((prev) => [...prev, ...uploadedFileInfo]);

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
        if (props.onUploadComplete) {
          props.onUploadComplete(result);
        }

        // Don't show alert since we're showing it in chat
        // alert(`Successfully uploaded ${selectedFiles.length} file(s) to chat`);
      } else {
        const errorData = await response.json();
        console.error("Upload failed:", errorData);
        alert(errorData.error || "Upload failed. Please try again.");
      }
    } catch (error) {
      console.error("Upload error:", error);
      alert("Upload failed. Please check your connection and try again.");
    }
  };

  const inferChatName = async (text, answer, chatId) => {
    const combinedText = `${text} ${answer}`;
    try {
      const response = await fetcher("infer-chat-name", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ messages: combinedText, chat_id: chatId }),
      });
      const data = await response.json();
      props.setCurrChatName(data.chat_name);
      props.handleForceUpdate();
    } catch (err) {
      console.error("Chat name inference failed", err);
    }
  };

  const pollForMessages = useCallback((chatId, maxAttempts = 3) => {
    let attempts = 0;

    const poll = async () => {
      attempts++;
      try {
        const res = await fetcher("retrieve-messages-from-chat", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ chat_id: chatId, chat_type: 0 }),
        });

        const data = await res.json();
        if (data.messages && data.messages.length > 0) {
          const formatted = data.messages.map((m) => ({
            id: m.id,
            chat_id: chatId,
            content: m.message_text,
            role: m.sent_from_user === 1 ? "user" : "assistant",
            relevant_chunks: m.relevant_chunks,
            reasoning: m.reasoning || [], // Include reasoning data from database
            sources: m.sources || [], // Include sources if available
            timestamp: new Date(m.created).getTime(), // Add timestamp from database
          }));
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
  }, []);

  // Function to fetch uploaded documents for a chat and create system messages
  const fetchUploadedDocuments = useCallback(async (chatId) => {
    try {
      const response = await fetcher("retrieve-current-docs", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: chatId }),
      });

      if (response.ok) {
        const result = await response.json();
        console.log("Backend doc_info response:", result.doc_info);
        if (result.doc_info && result.doc_info.length > 0) {
          // Create system messages for uploaded files
          const fileSystemMessages = result.doc_info.map((doc, index) => {
            console.log("Processing doc:", doc);
            return {
              id: `file-system-${doc.id}`,
              chat_id: chatId,
              role: "system",
              content: doc.documents
                ? doc.documents
                : `📎 Uploaded 1 file(s): ${doc.document_name}`,
              isFileUpload: true,
              uploadedFiles: [
                {
                  name: doc.document_name,
                  size: 0, // Size not available from database
                  uploadTime: doc.created || new Date().toISOString(), // Fallback if created is undefined
                  id: doc.id,
                },
              ],
              // Use current time so uploaded files appear at current position in chat
              timestamp: doc.created
                ? new Date(doc.created).getTime() + index
                : Date.now() + index,
            };
          });
          console.log(fileSystemMessages);
          return fileSystemMessages;
        }
      }
    } catch (error) {
      console.error("Error fetching uploaded documents:", error);
    }
    return [];
  }, []);

  const handleLoadChat = useCallback(async () => {
    if (!id) return;

    if (!props.selectedChatId) {
      props.handleChatSelect(id);
    }

    try {
      const res = await fetcher("retrieve-messages-from-chat", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_id: id, chat_type: 0 }),
      });

      const data = await res.json();

      console.log("res", data);
      props.setCurrChatName(data.chat_name);
      setChatNameGenerated(true);

      if (!data.messages?.length) {
        const pending =
          location.state?.message ||
          localStorage.getItem(`pending-message-${id}`);
        if (pending) {
          console.log(
            "[handleLoadChat] Loading pending message after new chat creation:",
            pending
          );
          const userMsg = {
            id: "user-content",
            chat_id: id,
            role: "user",
            content: pending,
            timestamp: Date.now(),
          };
          const thinkingMsg = {
            id: `thinking-${Date.now()}`,
            chat_id: id,
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
              `pending-message-${id}`,
              location.state.message
            );
          }
          await sendToAPI(pending, id, thinkingMsg.id);
          return;
        } else {
          setMessages([]);
        }
        return;
      }

      localStorage.removeItem(`pending-message-${id}`);
      const formatted = data.messages.map((m) => ({
        id: m.id,
        chat_id: id,
        content: m.message_text,
        role: m.sent_from_user === 1 ? "user" : "assistant",
        relevant_chunks: m.relevant_chunks,
        reasoning: m.reasoning || [], // Include reasoning data from database
        sources: m.sources || [], // Include sources if available
        timestamp: new Date(m.created).getTime(), // Add timestamp from database
      }));

      // Fetch uploaded documents and create system messages for them
      const fileSystemMessages = await fetchUploadedDocuments(id);

      // Combine regular messages with file system messages and sort by timestamp
      const allMessages = [...formatted, ...fileSystemMessages];

      // Sort messages by timestamp
      allMessages.sort((a, b) => {
        const aTime = a.timestamp || 0;
        const bTime = b.timestamp || 0;
        return aTime - bTime;
      });

      setMessages(allMessages);
    } catch (err) {
      console.error("Failed to load chat:", err);
    }
  }, [id, location.state?.message, fetchUploadedDocuments]);

  const handleSendMessage = async (event) => {
    event.preventDefault();
    console.log(
      "handleSendMessage called for user:",
      user ? "authenticated" : "guest"
    );

    if (!message.trim()) return;

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
    setMessage("");

    let targetChatId = id;

    const isNewChat =
      !id ||
      window.location.pathname === "/" ||
      window.location.pathname === "/chat";

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
          targetChatId = await props.createNewChat();
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
        timestamp: now + 1, // Slightly later timestamp for thinking message
      },
    ]);

    // Only store in localStorage for authenticated user chats
    if (user) {
      localStorage.setItem(`pending-message-${targetChatId}`, currentMessage);
    }
    await sendToAPI(currentMessage, targetChatId, thinkingId);
  };

  const sendToAPI = async (text, chatId, thinkingId) => {
    try {
      // Check if this is a guest chat
      const isGuestChat =
        (typeof chatId === "string" && chatId.startsWith("guest-")) ||
        (!user && chatId === null); // Also detect guest mode when no user and chatId is null

      if (isDev) {
        console.log("sendToAPI called with:", {
          text,
          chatId,
          isGuestChat,
          user: !!user,
        });
      }

      const res = await fetcher("process-message-pdf", {
        method: "POST",
        isGuest: isGuestChat, // Only set isGuest for actual guest chats
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          chat_id: isGuestChat ? null : Number(chatId), // Send null for guest chats
          model_type: props.isPrivate,
          model_key: props.confirmedModelKey,
          is_guest: isGuestChat, // Flag to indicate guest chat
        }),
      });

      if (isDev) {
        console.log("API response status:", res.status);
      }
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }

      await handleSSEStreamingResponse(res, thinkingId, text, chatId);

      // Only remove from localStorage for authenticated user chats
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
  };

  const handleSSEStreamingResponse = async (
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
                !isGuestChat
              ) {
                await inferChatName(originalText, eventData.answer, chatId);
                setChatNameGenerated(true);
                props.handleForceUpdate?.();
              }

              // Force final state update for completion events
              if (
                eventData.type === "complete" ||
                eventData.type === "step-complete"
              ) {
                setTimeout(() => {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === thinkingId
                        ? {
                            ...msg,
                            isThinking: false,
                            currentStep: null,
                            content: eventData.answer || msg.content,
                            sources: eventData.sources || msg.sources || [],
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
  };

  const updateMessageWithStreamData = (message, eventData) => {
    const updatedMessage = { ...message };

    console.log("Processing event:", eventData);

    switch (eventData.type) {
      case "tool_start":
      case "tools_start":
        // Add reasoning step for tool start
        const toolStartStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          tool_name: eventData.tool_name,
          message: `Using ${eventData.tool_name}...`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          toolStartStep,
        ];
        updatedMessage.currentStep = toolStartStep;
        break;

      case "tool_end":
        // Update the last tool step with output
        const reasoningWithOutput = [...(updatedMessage.reasoning || [])];
        const lastToolIndex = reasoningWithOutput.findLastIndex(
          (step) => step.type === "tool_start" || step.type === "tools_start"
        );
        if (lastToolIndex !== -1) {
          reasoningWithOutput[lastToolIndex] = {
            ...reasoningWithOutput[lastToolIndex],
            tool_output: eventData.output,
            message: "Tool execution completed",
          };
        }
        updatedMessage.reasoning = reasoningWithOutput;
        updatedMessage.currentStep = {
          type: "tool_end",
          message: "Tool execution completed",
        };
        break;

      case "agent_thinking":
        // Add thinking step
        const thinkingStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_thought: eventData.thought,
          planned_action: eventData.action,
          message: "Planning next step...",
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          thinkingStep,
        ];
        updatedMessage.currentStep = thinkingStep;
        break;

      case "complete":
        // Set final answer and sources
        updatedMessage.content = eventData.answer || "";
        updatedMessage.sources = eventData.sources || [];
        updatedMessage.isThinking = false;
        updatedMessage.currentStep = null;

        // Add completion step to reasoning
        const completeStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          thought: eventData.thought,
          message: "Response complete",
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          completeStep,
        ];
        break;
      case "step-complete":
        // Set final answer and sources
        updatedMessage.content = eventData.answer || "";
        updatedMessage.sources = eventData.sources || [];
        updatedMessage.isThinking = false;
        updatedMessage.currentStep = null;

        // Add completion step to reasoning
        const StepComplete = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          thought: eventData.thought,
          message: "Query processing completed",
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          StepComplete,
        ];
        break;

      // Multi-agent system event types
      case "agent_start":
        const agentStartStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          message: eventData.message || `${eventData.agent_name} started`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          agentStartStep,
        ];
        updatedMessage.currentStep = agentStartStep;
        break;

      case "agent_progress":
        const progressStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          current_agent: eventData.current_agent,
          completed_agents: eventData.completed_agents,
          message: eventData.message || `${eventData.current_agent} completed`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          progressStep,
        ];
        break;

      case "agent_reasoning":
        const reasoningStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          reasoning: eventData.reasoning,
          message: `${eventData.agent_name} reasoning`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          reasoningStep,
        ];
        break;

      case "agent_tool_use":
        const agentToolStep = {
          id: `step-${Date.now()}`,
          type: eventData.type,
          agent_name: eventData.agent_name,
          tool_name: eventData.tool_name,
          input: eventData.input,
          message:
            eventData.message ||
            `${eventData.agent_name} using ${eventData.tool_name}`,
          timestamp: Date.now(),
        };
        updatedMessage.reasoning = [
          ...(updatedMessage.reasoning || []),
          agentToolStep,
        ];
        break;

      case "agent_tool_complete":
        // Update the last agent tool step with output
        const agentReasoningWithOutput = [...(updatedMessage.reasoning || [])];
        const lastAgentToolIndex = agentReasoningWithOutput.findLastIndex(
          (step) => step.type === "agent_tool_use"
        );
        if (lastAgentToolIndex !== -1) {
          agentReasoningWithOutput[lastAgentToolIndex] = {
            ...agentReasoningWithOutput[lastAgentToolIndex],
            tool_output: eventData.output,
            message: eventData.message || "Agent tool execution completed",
          };
        }
        updatedMessage.reasoning = agentReasoningWithOutput;
        break;

      case "reasoning_step":
        // Add reasoning step from multi-agent system
        if (eventData.step) {
          updatedMessage.reasoning = [
            ...(updatedMessage.reasoning || []),
            eventData.step,
          ];
        }
        break;

      default:
        console.warn("Unhandled event type:", eventData.type);
    }

    return updatedMessage;
  };

  // Component for displaying thinking steps
  const ThinkingIndicator = ({ step }) => {
    const getStepIcon = (type) => {
      switch (type) {
        case "llm_reasoning":
          return <FontAwesomeIcon icon={faBrain} className="text-accent" />;
        case "tool_start":
        case "tools_start":
        case "tool_end":
          return <FontAwesomeIcon icon={faSearch} className="text-accent" />;
        case "agent_thinking":
          return <FontAwesomeIcon icon={faCog} className="text-accent" />;
        case "complete":
        case "step-complete":
          return (
            <FontAwesomeIcon icon={faCheckCircle} className="text-accent" />
          );
        // Multi-agent system icons
        case "agent_start":
          return <FontAwesomeIcon icon={faCog} className="text-accent" />;
        case "agent_progress":
          return (
            <FontAwesomeIcon icon={faArrowRight} className="text-accent" />
          );
        case "agent_reasoning":
          return <FontAwesomeIcon icon={faBrain} className="text-accent" />;
        case "agent_tool_use":
        case "agent_tool_complete":
          return <FontAwesomeIcon icon={faSearch} className="text-accent" />;
        case "agent_completion":
        case "agent_error":
          return (
            <FontAwesomeIcon icon={faInfoCircle} className="text-accent" />
          );
        case "orchestrator_decision":
        case "orchestrator_synthesis":
          return <FontAwesomeIcon icon={faSitemap} className="text-accent" />;
        case "reasoning_step":
          return <FontAwesomeIcon icon={faLightbulb} className="text-accent" />;
        default:
          return <FontAwesomeIcon icon={faCog} className="text-accent" />;
      }
    };
    console.log("stepsss", step);
    const getStepColor = (type) => {
      switch (type) {
        case "llm_reasoning":
          return "border-l-accent bg-accent/10";
        case "tool_start":
        case "tools_start":
        case "tool_end":
          return "border-l-accent bg-accent/10";
        case "agent_thinking":
          return "border-l-accent bg-accent/10";
        case "complete":
        case "step-complete":
          return "border-l-accent bg-accent/20";
        // Multi-agent system colors
        case "agent_start":
          return "border-l-accent bg-accent/10";
        case "agent_progress":
          return "border-l-accent bg-accent/10";
        case "agent_reasoning":
          return "border-l-accent bg-accent/10";
        case "agent_tool_use":
        case "agent_tool_complete":
          return "border-l-accent bg-accent/10";
        case "agent_completion":
          return "border-l-accent bg-accent/10";
        case "agent_error":
          return "border-l-red-400 bg-red-950/20";
        case "orchestrator_decision":
        case "orchestrator_synthesis":
          return "border-l-accent bg-accent/10";
        case "reasoning_step":
          return "border-l-accent bg-accent/10";
        default:
          return "border-l-gray-400 bg-gray-800/20";
      }
    };
    console.log(`${step.message || "Processing"}: `, step);
    if (!step) return null;
    return (
      <div
        className={`border-l-2 ${getStepColor(
          step.type
        )} pl-3 py-2 mb-2 text-sm`}
      >
        <div className="flex items-center gap-2 mb-1">
          {getStepIcon(step.type)}
          <span className="text-gray-300 font-medium">
            {step.message || "Processing..."}
          </span>
        </div>

        {step.thought && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Thought:</strong> {step.thought}
          </div>
        )}

        {step.agent_thought && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Planning:</strong> {step.agent_thought}
          </div>
        )}

        {step.tool_name && (
          <div className="text-gray-500 text-xs">
            <strong>Tool:</strong> {step.tool_name}
          </div>
        )}

        {step.tool_output && (
          <div className="text-gray-500 text-xs mt-1">
            <strong>Result:</strong>{" "}
            {step.tool_output.length > 100
              ? step.tool_output.substring(0, 100) + "..."
              : step.tool_output}
          </div>
        )}

        {/* Multi-agent system specific fields */}
        {step.agent_name && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Agent:</strong> {step.agent_name}
          </div>
        )}

        {step.reasoning && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Reasoning:</strong>{" "}
            {step.reasoning.length > 150
              ? step.reasoning.substring(0, 150) + "..."
              : step.reasoning}
          </div>
        )}

        {step.current_agent && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Current Agent:</strong> {step.current_agent}
          </div>
        )}

        {step.completed_agents && step.completed_agents.length > 0 && (
          <div className="text-gray-500 text-xs">
            <strong>Completed:</strong> {step.completed_agents.join(", ")}
          </div>
        )}

        {step.final_thought && (
          <div className="text-gray-400 text-xs mb-1">
            <strong>Final Thought:</strong> {step.final_thought}
          </div>
        )}

        {step.planned_action && (
          <div className="text-gray-500 text-xs">
            <strong>Planned Action:</strong> {step.planned_action}
          </div>
        )}

        {step.confidence && (
          <div className="text-gray-500 text-xs">
            <strong>Confidence:</strong> {Math.round(step.confidence * 100)}%
          </div>
        )}

        {step.error && (
          <div className="text-red-400 text-xs mt-1">
            <strong>Error:</strong> {step.error}
          </div>
        )}
      </div>
    );
  };

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

    if (id) {
      handleLoadChat();
    } else {
      setMessages([]);
      setChatNameGenerated(false);
      setUploadedFiles([]); // Clear uploaded files when switching chats
    }

    return () => {
      if (pollingTimeoutRef.current) {
        clearTimeout(pollingTimeoutRef.current);
        pollingTimeoutRef.current = null;
      }
    };
  }, [id, handleLoadChat]);

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
      } flex flex-col ${props.menu ? "md:blur-none blur" : ""}`}
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
                        </div>
                      ) : (
                        <div>
                          {/* Main response content */}
                          <p className="whitespace-pre-wrap leading-relaxed text-sm">
                            {msg.content}
                          </p>
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
            What can I help you with?
          </div>
        )}

        {/* Banner above chat input */}
        <div className="w-full max-w-4xl mx-auto mb-4 px-4">
          {!user && (
            // Guest user info banner
            <div className="bg-gradient-to-r from-blue-600/20 to-purple-600/20 border border-blue-500/30 rounded-lg p-4 mb-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FontAwesomeIcon
                    icon={faInfoCircle}
                    className="text-blue-400 text-lg flex-shrink-0"
                  />
                  <div className="text-white">
                    <p className="text-sm font-medium text-blue-200">
                      Guest Mode
                    </p>
                    <p className="text-xs text-gray-300 mt-1">
                      You're chatting as a guest. Log in to unlock advanced
                      features and save your chats.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() =>
                    window.dispatchEvent(new CustomEvent("showLogin"))
                  }
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex-shrink-0"
                >
                  Login
                </button>
              </div>
            </div>
          )}
          {user && numCredits === 0 && (
            // Out of credits banner (only for authenticated users)
            <div className="bg-gradient-to-r from-red-600/20 to-orange-600/20 border border-red-500/30 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <FontAwesomeIcon
                    icon={faExclamationTriangle}
                    className="text-red-400 text-lg flex-shrink-0"
                  />
                  <div className="text-white">
                    <p className="text-sm font-medium text-red-200">
                      No Credits Remaining
                    </p>
                    <p className="text-xs text-gray-300 mt-1">
                      You've run out of credits. Please upgrade to continue
                      using AI analysis.
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => setShowUpgradeModal(true)}
                  className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors flex-shrink-0"
                >
                  Upgrade Now
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Input form */}
        <div className="flex w-full justify-center mb-4 px-4">
          <div className="flex items-center gap-1 focus-within:ring-slate-600 focus-within:ring-2 border-gray-600 p-2 rounded-xl bg-sidebar w-full max-w-4xl">
            {/* Left side - Upload button */}
            <button
              type="button"
              onClick={() => {
                console.log(
                  "Upload button clicked in Chatbot",
                  "selectedChatId:",
                  props.selectedChatId
                );
                setShowFileUpload(true);
                setUploadButtonClicked(true);
                setTimeout(() => setUploadButtonClicked(false), 1000);
              }}
              disabled={props.isUploading || (!user ? false : numCredits === 0)}
              className={`flex items-center justify-center w-12 h-12 rounded-lg transition-colors flex-shrink-0 ${
                uploadButtonClicked
                  ? "bg-gray-600 text-white"
                  : props.isUploading
                  ? "bg-gray-500 text-gray-300 cursor-not-allowed"
                  : "bg-gray-600 hover:bg-gray-500 text-white"
              }`}
              title={
                !id
                  ? "Please select or create a chat first"
                  : !user
                  ? "Add files (login for enhanced features)"
                  : "Add files"
              }
            >
              <FontAwesomeIcon icon={faFile} className="text-lg" />
            </button>

            {/* Center - Input */}
            <div className="flex-1">
              <div className="relative">
                <div className="relative flex items-center rounded-lg focus-within:border-accent  focus-within:ring-0 transition-all duration-200">
                  <textarea
                    className="w-full  border-none disabled:cursor-not-allowed  resize-none text-base px-4 py-3 focus:ring-0 focus:outline-none text-white placeholder:text-gray-400 bg-transparent rounded-lg"
                    rows={1}
                    placeholder={
                      !user
                        ? "Ask your question (guest mode)"
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
            </div>

            {/* Right side - Send button */}
            <button
              type="button"
              onClick={handleSendMessage}
              disabled={
                !message ||
                message.trim() === "" ||
                messages.some((msg) => msg.isThinking)
              }
              className={`flex items-center justify-center w-12 h-12 rounded-lg transition-colors flex-shrink-0 ${
                !message ||
                message.trim() === "" ||
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
