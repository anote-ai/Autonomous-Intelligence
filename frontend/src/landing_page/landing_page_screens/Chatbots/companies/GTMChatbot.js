import React, { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPaperPlane, faUndoAlt } from "@fortawesome/free-solid-svg-icons";
import { useLandingChatApi } from "../useLandingChatApi";

const GTMChatbot = () => {
  const [file, setFile] = useState(null);
  const [messages, setMessages] = useState([
    {
      message: "Hello, I’m your Anote chatbot. How can I help you today?",
      direction: "incoming",
    },
  ]);
  const inputRef = useRef(null);
  const scrollRef = useRef(null);
  const fileInputRef = useRef(null);
  const { sendMultipartChat } = useLandingChatApi();

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  const sendMessage = async (text) => {
    console.log("🟡 Attempting to send:", text);
    if (!text.trim()) return;
    inputRef.current.value = "";

    const tempId = Date.now();
    const newMessages = [
      ...messages,
      { message: text, direction: "outgoing" },
      { message: "Loading...", direction: "incoming", id: tempId },
    ];
    setMessages(newMessages);

    // Convert full history to OpenAI format
    const openAIMessages = [
      ...messages
        .filter((msg) => !msg.id) // skip loading messages
        .map((msg) => ({
          role: msg.direction === "outgoing" ? "user" : "assistant",
          content: msg.message,
        })),
      { role: "user", content: text },
    ];

    try {
      const formData = new FormData();
      formData.append("prompt", text);
      formData.append("messages", JSON.stringify(openAIMessages));
      if (file) {
        formData.append("file", file);
      }

      console.log("Sending message:", text);

      const data = await sendMultipartChat("/gtm/respond", formData);

      console.log("Received response:", data);

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? { message: data.response, direction: "incoming" }
            : msg
        )
      );
      // setFile(null); // Clear file after successful send
    } catch (e) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === tempId
            ? { message: "Error connecting to server.", direction: "incoming" }
            : msg
        )
      );
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage(inputRef.current.value);
    }
  };

  return (
    <div className="bg-[#1a1a1a] text-white h-[70vh] rounded-2xl p-4 flex flex-col">
      {/* Header */}
      <div className="flex justify-between items-center mb-2">
        <FontAwesomeIcon icon={faUndoAlt} className="cursor-pointer text-white" />
        <h2 className="text-lg font-semibold">Anote</h2>
        <div></div>
      </div>
      <hr className="border-gray-600 mb-2" />

      {/* Chat messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-2 pr-2"
      >
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`flex ${msg.direction === "incoming" ? "justify-start" : "justify-end"}`}
          >
            <div
              className="rounded-2xl px-4 py-2 max-w-[75%] bg-[#2e2e2e] text-white"
            >
              {msg.message}
            </div>
          </div>
        ))}
      </div>

      {/* Input field */}
      <div className="flex items-center mt-4">
        <input
          ref={inputRef}
          type="text"
          placeholder="Type your message..."
          onKeyDown={handleKeyPress}
          className="flex-grow px-4 py-2 rounded-xl bg-[#141414] text-white border border-[#9b9b9b] focus:outline-none focus:ring-1 focus:ring-white placeholder:text-[#9B9B9B]"
        />
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.csv"
          onChange={(e) => setFile(e.target.files[0])}
          className="text-sm text-gray-400"
        />     
        <button
          onClick={() => {
            setFile(null);
            if (fileInputRef.current) {
              fileInputRef.current.value = ""; // Clear the native file input
            }
          }}
          className="ml-2 text-sm text-gray-400 underline"
        >
          X
        </button>
        <button
          onClick={() => sendMessage(inputRef.current.value)}
          className="ml-3 bg-[#3A3B41] p-3 rounded-xl text-white"
        >
          <FontAwesomeIcon icon={faPaperPlane} />
        </button>
      </div>
    </div>
  );
};

export default GTMChatbot;
