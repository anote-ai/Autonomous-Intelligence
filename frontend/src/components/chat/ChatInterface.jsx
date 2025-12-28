import React, { useState } from "react";
import { useTheme } from "../../hooks/useTheme";

const ChatInterface = ({ isSidebarOpen, isAuthenticated }) => {
  const { theme } = useTheme();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [showOptions, setShowOptions] = useState(false);

  const menuOptions = [
    {
      id: 1,
      label: "Attach File",
      icon: "M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13",
    },
    {
      id: 2,
      label: "Upload Image",
      icon: "M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z",
    },
    {
      id: 3,
      label: "Upload Document",
      icon: "M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z",
    },
  ];

  const handleSendMessage = () => {
    if (inputValue.trim()) {
      setMessages([
        ...messages,
        { id: Date.now(), text: inputValue, sender: "user" },
      ]);
      setInputValue("");
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
        isSidebarOpen ? "md:ml-24" : ""
      } pt-12`}
    >
      {messages.length === 0 ? (
        /* Centered Input when no messages */
        <div
          className={`flex-1 flex items-center justify-center py-4 ${
            theme === "dark" ? "bg-gray-900" : "bg-gray-50"
          }`}
        >
          <div className="w-full max-w-5xl mx-auto px-4">
            <div
              className={`flex items-center gap-2 rounded-lg border px-3 py-2 relative ${
                theme === "dark"
                  ? "border-gray-600 bg-gray-700"
                  : "border-gray-300 bg-white"
              }`}
            >
              {/* Plus button with dropdown */}
              <div className="relative group">
                <button
                  onClick={() =>
                    isAuthenticated && setShowOptions(!showOptions)
                  }
                  disabled={!isAuthenticated}
                  className={`p-1 rounded transition-colors ${
                    isAuthenticated
                      ? theme === "dark"
                        ? "hover:bg-gray-600"
                        : "hover:bg-gray-200"
                      : "opacity-50 cursor-not-allowed"
                  }`}
                >
                  <svg
                    className={`w-5 h-5 ${
                      theme === "dark" ? "text-gray-400" : "text-gray-500"
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 4v16m8-8H4"
                    />
                  </svg>
                </button>
                {!isAuthenticated && (
                  <div className="absolute bottom-full left-0 mb-2 w-48 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity">
                    <div
                      className={`text-xs px-3 py-2 rounded shadow-lg ${
                        theme === "dark"
                          ? "bg-gray-800 text-gray-200"
                          : "bg-gray-700 text-white"
                      }`}
                    >
                      Login to use tools
                    </div>
                  </div>
                )}

                {/* Dropdown menu */}
                {showOptions && (
                  <div
                    className={`absolute bottom-full left-0  w-48 rounded-lg shadow-lg border overflow-hidden z-10 ${
                      theme === "dark"
                        ? "bg-gray-700 border-gray-600"
                        : "bg-white border-gray-300"
                    }`}
                  >
                    {menuOptions.map((option) => (
                      <button
                        key={option.id}
                        className={`w-full px-4 py-2 text-left flex items-center gap-2 transition-colors ${
                          theme === "dark"
                            ? "text-white hover:bg-gray-600"
                            : "text-gray-900 hover:bg-gray-50"
                        }`}
                      >
                        <svg
                          className="w-5 h-5"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d={option.icon}
                          />
                        </svg>
                        {option.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Input field */}
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Type your message..."
                className={`flex-1 bg-transparent focus:outline-none ${
                  theme === "dark"
                    ? "text-white placeholder-gray-400"
                    : "text-gray-900 placeholder-gray-500"
                }`}
              />

              {/* Send button */}
              <button
                onClick={handleSendMessage}
                disabled={!inputValue.trim()}
                className="p-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <svg
                  className="w-5 h-5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                  />
                </svg>
              </button>
            </div>
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
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.sender === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div
                    className={`max-w-[70%] rounded-lg px-4 py-2 ${
                      message.sender === "user"
                        ? "bg-blue-500 text-white"
                        : theme === "dark"
                        ? "bg-gray-800 text-white"
                        : "bg-white text-gray-900"
                    }`}
                  >
                    {message.text}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Chat Input Area - fixed at bottom */}
          <div
            className={`py-4 ${
              theme === "dark" ? "bg-gray-900" : "bg-gray-50"
            }`}
          >
            <div className="w-full max-w-5xl mx-auto px-4">
              <div
                className={`flex items-center gap-2 rounded-lg border px-3 py-2 relative ${
                  theme === "dark"
                    ? "border-gray-600 bg-gray-700"
                    : "border-gray-300 bg-white"
                }`}
              >
                {/* Plus button with dropdown */}
                <div className="relative group">
                  <button
                    onClick={() =>
                      isAuthenticated && setShowOptions(!showOptions)
                    }
                    disabled={!isAuthenticated}
                    className={`p-1 rounded transition-colors ${
                      isAuthenticated
                        ? theme === "dark"
                          ? "hover:bg-gray-600"
                          : "hover:bg-gray-200"
                        : "opacity-50 cursor-not-allowed"
                    }`}
                  >
                    <svg
                      className={`w-5 h-5 ${
                        theme === "dark" ? "text-gray-400" : "text-gray-500"
                      }`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 4v16m8-8H4"
                      />
                    </svg>
                  </button>
                  {!isAuthenticated && (
                    <div className="absolute bottom-full left-0 mb-2 w-48 opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity">
                      <div
                        className={`text-xs px-3 py-2 rounded shadow-lg ${
                          theme === "dark"
                            ? "bg-gray-800 text-gray-200"
                            : "bg-gray-700 text-white"
                        }`}
                      >
                        Login to use tools
                      </div>
                    </div>
                  )}

                  {/* Dropdown menu */}
                  {showOptions && (
                    <div
                      className={`absolute bottom-full left-0 mb-3 w-48 rounded-lg shadow-lg border overflow-hidden z-10 ${
                        theme === "dark"
                          ? "bg-gray-700 border-gray-600"
                          : "bg-white border-gray-300"
                      }`}
                    >
                      {menuOptions.map((option) => (
                        <button
                          key={option.id}
                          className={`w-full cursor-pointer px-4 py-2 text-left flex items-center gap-2 transition-colors ${
                            theme === "dark"
                              ? "text-white hover:bg-gray-600"
                              : "text-gray-900 hover:bg-gray-50"
                          }`}
                        >
                          <svg
                            className="w-5 h-5"
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d={option.icon}
                            />
                          </svg>
                          <span className="text-sm">{option.label}</span>
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                {/* Input field */}
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={handleKeyPress}
                  placeholder="Type your message..."
                  className={`flex-1 bg-transparent focus:outline-none ${
                    theme === "dark"
                      ? "text-white placeholder-gray-400"
                      : "text-gray-900 placeholder-gray-500"
                  }`}
                />

                {/* Send button */}
                <button
                  onClick={handleSendMessage}
                  disabled={!inputValue.trim()}
                  className="p-1.5 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <svg
                    className="w-5 h-5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
                    />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ChatInterface;
