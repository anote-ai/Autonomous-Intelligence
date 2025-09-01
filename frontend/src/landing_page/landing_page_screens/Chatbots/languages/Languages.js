import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";

const LANGUAGE_MODELS = {
  korean: "GPT-4.1",
  spanish: "GPT-4.1",
  japanese: "GPT-4.1",
  arabic: "GPT-4.1",
  chinese: "GPT-4.1",
};

const API_BASE = process.env.REACT_APP_BACK_END_HOST || "";
const LANGUAGE_API_ENDPOINTS = {
  spanish: `${API_BASE}/api/chat/spanish`,
  korean: `${API_BASE}/api/chat/korean`,
  japanese: `${API_BASE}/api/chat/japanese`,
  arabic: `${API_BASE}/api/chat/arabic`,
  chinese: `${API_BASE}/api/chat/chinese`,
};

const validLanguages = Object.keys(LANGUAGE_MODELS);
const Languages = () => {
    const { lang } = useParams();
    const initialLang = validLanguages.includes(lang) ? lang : "spanish";
    const [selectedLanguage, setSelectedLanguage] = useState(initialLang);
    const navigate = useNavigate();

    // Hooks must be called always, so move this above the early return
    const [messages, setMessages] = useState([
      { message: "Hello! Choose a language and start chatting.", direction: "incoming" },
    ]);
    const inputRef = useRef(null);
    const scrollRef = useRef(null);
    const [file, setFile] = useState(null);
    const fileInputRef = useRef(null);

    // Redirect to Spanish if no language is selected
    useEffect(() => {
        if (!lang || !validLanguages.includes(lang)) {
        navigate("/languages/spanish", { replace: true });
        }
    }, [lang, navigate]);


  // Update selectedLanguage when URL param changes
    useEffect(() => {
        if (lang && validLanguages.includes(lang)) {
          setSelectedLanguage(lang);
          setMessages([
            { message: "Hello! Choose a language and start chatting.", direction: "incoming" },
          ]);
          setFile(null);
          if (fileInputRef.current) fileInputRef.current.value = "";
        }
      }, [lang]);

    useEffect(() => {
        scrollRef.current?.scrollTo({
          top: scrollRef.current.scrollHeight,
          behavior: "smooth",
        });
      }, [messages]);

    if (!lang || !validLanguages.includes(lang)) return null;


    const sendMessage = async (text) => {
      console.log("🟡 Attempting to send:", text);
      if (!text.trim()) return;
      inputRef.current.value = "";

      const tempId = Date.now();
      setMessages((prev) => [
        ...prev,
        { message: text, direction: "outgoing" },
        { message: "Thinking...", direction: "incoming", id: tempId },
      ]);

    //Chatbot remembers convo
    const openAIMessages = [

      //Convert local messages to OpenAI format
      ...messages
        .filter(msg => !msg.id)
        .map(msg => ({
          role: msg.direction === "outgoing" ? "user" : "assistant",
          content: msg.message,
        })),
      //Add the new message
      { role: "user", content: text },
    ];

      try {
        const apiUrl = LANGUAGE_API_ENDPOINTS[selectedLanguage] || "/api/chat/spanish";
        const formData = new FormData();
        formData.append("prompt", text);
        formData.append("messages", JSON.stringify(openAIMessages));
        if (file) {
          formData.append("file", file);
        }

        console.log("Sending message:", text);

        const res = await fetch(apiUrl, {
          method: "POST",
          // headers: { "Content-Type": "application/json" },
          body: formData,
        });

        const data = await res.json();

        console.log("Received response:", res);

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempId
              ? { message: data.response, direction: "incoming" }
              : msg
          )
        );
      } catch (error) {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === tempId
              ? { message: "❌ Error fetching response.", direction: "incoming" }
              : msg
          )
        );
      }
    };

    const handleKeyPress = (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault(); // stops newline
        sendMessage(inputRef.current.value);
      }
    };

    // ... rest of your JSX remains unchanged
  return (
  <section className="min-h-screen bg-[#111827] text-white p-8">
    {/* Title */}
    <h1 className="text-4xl font-bold text-center mb-10 tracking-tight">
    <span className="text-[#defe47]">
  Languages
    </span>
    </h1>

    {/* Main Layout */}
    <div className="flex flex-col md:flex-row gap-10 justify-center items-start">
      {/* Language Selector */}
      <div className="w-full md:w-1/4 flex flex-col items-center md:items-start">
        <select
          value={selectedLanguage}
          onChange={(e) => {
            const lang = e.target.value;
            setSelectedLanguage(lang);
            navigate(`/languages/${lang.toLowerCase()}`);
          }}
          className="bg-[#1f2937] text-white border border-gray-700 rounded-md px-4 py-2 w-full focus:outline-none focus:ring-2 focus:ring-[#defe47]"
        >
          {Object.keys(LANGUAGE_MODELS).map((lang) => (
            <option key={lang} value={lang}>
              {lang.charAt(0).toUpperCase() + lang.slice(1)}
            </option>
          ))}
        </select>

        <p className="text-xs text-gray-400 mt-3">
          Model:{" "}
          <span className="text-[#defe47] font-medium">
            {LANGUAGE_MODELS[selectedLanguage]}
          </span>
        </p>

        <p className="text-[10px] text-gray-500 mt-4 text-center md:text-left">
          Each language uses the best model from our{" "}
          <a href="/models" className="underline text-[#28b2fb] hover:text-white transition">
            leaderboard
          </a>
          .
        </p>
      </div>

      {/* Chat UI */}
      <div className="w-full md:w-3/4 bg-[#1f2937] rounded-2xl p-6 h-[70vh] flex flex-col shadow-xl">
        {/* Header */}
        <div className="flex justify-between items-center mb-3">
          <div />
          <h2 className="text-md font-semibold text-white tracking-wide">Chat</h2>
          <div className="text-sm text-[#defe47] font-mono">
            {LANGUAGE_MODELS[selectedLanguage]}
          </div>
        </div>

        <hr className="border-gray-700 mb-3" />

        {/* Messages */}
        <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-2 pr-2 custom-scrollbar">
          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex ${
                msg.direction === "incoming" ? "justify-start" : "justify-end"
              }`}
            >
              <div
                className={`rounded-xl px-4 py-3 max-w-[75%] text-sm ${
                  msg.direction === "incoming"
                    ? "bg-[#2c3745] text-white"
                    : "bg-[#28b2fb] text-black"
                }`}
              >
                {msg.message}
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <div className="flex items-center mt-4 gap-2">
          <textarea
            ref={inputRef}
            type="text"
            placeholder="Type your message..."
            onKeyDown={handleKeyPress}
            className="flex-grow px-4 py-3 rounded-xl bg-[#0f172a] text-white border border-gray-700 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-[#defe47] text-sm resize-none"
          />

          {/* File Upload */}
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx,.txt,.csv"
            onChange={(e) => setFile(e.target.files[0])}
            className="text-xs text-gray-400"
          />
          {file && (
            <button
              onClick={() => {
                setFile(null);
                if (fileInputRef.current) fileInputRef.current.value = "";
              }}
              className="text-xs text-red-400 underline ml-1"
            >
              Clear
            </button>
          )}

          {/* Submit Button */}
          <button
            onClick={() => sendMessage(inputRef.current.value)}
            className="bg-[#defe47] hover:bg-[#c4e232] text-black px-4 py-2 rounded-xl font-semibold transition"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  </section>
);
}
  export default Languages;