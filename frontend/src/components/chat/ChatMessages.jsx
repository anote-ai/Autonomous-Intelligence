import React, { useState } from "react";
import { useTheme } from "../../hooks/useTheme";
import FileViewerModal from "../common/FileViewerModal";
import { FILE_ATTACHMENT_INDICATOR } from "../../constants/messages";

const ChatMessages = ({ messages, isLoading, error }) => {
  const { theme } = useTheme();
  const [selectedFile, setSelectedFile] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const handleFileClick = (file, e) => {
    e.preventDefault();
    setSelectedFile(file);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setSelectedFile(null);
  };

  const isImageFile = (filename) => {
    const imageExtensions = [
      ".png",
      ".jpg",
      ".jpeg",
      ".gif",
      ".bmp",
      ".webp",
      ".svg",
    ];
    return imageExtensions.some((ext) => filename.toLowerCase().endsWith(ext));
  };

  const isPdfFile = (filename) => {
    return filename.toLowerCase().endsWith(".pdf");
  };

  const getFileIcon = (filename) => {
    if (isPdfFile(filename)) {
      return (
        <svg className="w-full h-full" fill="currentColor" viewBox="0 0 24 24">
          <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm4 18H6V4h7v5h5v11zM8 15h8v2H8v-2zm0-4h8v2H8v-2zm0-4h5v2H8V7z" />
        </svg>
      );
    }
    return (
      <svg
        className="w-full h-full"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
        />
      </svg>
    );
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return "";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
          <p
            className={`mt-2 text-sm ${
              theme === "dark" ? "text-gray-400" : "text-gray-600"
            }`}
          >
            Loading messages...
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center py-8">
        <div
          className={`text-center p-4 rounded-lg ${
            theme === "dark"
              ? "bg-red-900/20 text-red-400"
              : "bg-red-100 text-red-600"
          }`}
        >
          <p className="font-semibold">Error loading messages</p>
          <p className="text-sm mt-1">{error}</p>
        </div>
      </div>
    );
  }

  if (!messages || messages.length === 0) {
    return null;
  }

  return (
    <>
      <div className="space-y-4">
        {messages.map((message) => {
          // Skip messages that have no text and no files (empty messages)
          const hasText =
            message.text && !message.text.startsWith(FILE_ATTACHMENT_INDICATOR);
          const hasFiles = message.files && message.files.length > 0;

          if (!hasText && !hasFiles) {
            return null;
          }

          return (
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
                {/* Display files if they exist */}
                {message.files && message.files.length > 0 && (
                  <div className="mb-2 space-y-2">
                    {message.files.map((file, index) => {
                      const isImage = isImageFile(file.name);

                      if (isImage) {
                        // Display image inline
                        return (
                          <div key={index} className="rounded overflow-hidden">
                            <img
                              src={file.url}
                              alt={file.name}
                              className="max-w-full h-auto cursor-pointer rounded hover:opacity-90 transition-opacity"
                              style={{
                                maxHeight: "300px",
                                objectFit: "contain",
                              }}
                            />
                            <div
                              className={`text-xs mt-1 ${
                                message.sender === "user"
                                  ? "text-blue-100"
                                  : theme === "dark"
                                    ? "text-gray-400"
                                    : "text-gray-500"
                              }`}
                            ></div>
                          </div>
                        );
                      }

                      // Display non-image files as attachment buttons
                      const isPdf = isPdfFile(file.name);
                      return (
                        <button
                          key={index}
                          onClick={(e) => handleFileClick(file, e)}
                          className={`group relative w-full flex items-center gap-2 p-2.5 rounded-lg border transition-all duration-200 overflow-hidden ${
                            message.sender === "user"
                              ? isPdf
                                ? "border-white/40 bg-transparent hover:bg-white/10 shadow-md hover:shadow-lg"
                                : "border-white/40 bg-transparent hover:bg-white/10"
                              : theme === "dark"
                                ? isPdf
                                  ? "border-red-500/50 bg-linear-to-br from-red-900/40 to-red-800/40 hover:from-red-800/50 hover:to-red-700/50 shadow-md hover:shadow-red-500/20"
                                  : "border-gray-600 bg-gray-700 hover:bg-gray-600"
                                : isPdf
                                  ? "border-red-200 bg-linear-to-br from-red-50 to-red-100 hover:from-red-100 hover:to-red-200 shadow-sm hover:shadow-md"
                                  : "border-gray-300 bg-gray-100 hover:bg-gray-200"
                          }`}
                        >
                          {/* Icon */}
                          <div
                            className={`shrink-0 p-1.5 rounded-md ${
                              message.sender === "user"
                                ? isPdf
                                  ? "bg-white/20 text-white"
                                  : "bg-blue-500/30 text-white"
                                : theme === "dark"
                                  ? isPdf
                                    ? "bg-red-500/30 text-red-300"
                                    : "bg-gray-600 text-gray-300"
                                  : isPdf
                                    ? "bg-red-500/20 text-red-700"
                                    : "bg-gray-200 text-gray-700"
                            }`}
                          >
                            <div className="w-5 h-5">
                              {getFileIcon(file.name)}
                            </div>
                          </div>

                          {/* File Info */}
                          <div className="flex-1 min-w-0 text-left">
                            <div
                              className={`font-semibold truncate text-sm ${
                                message.sender === "user"
                                  ? "text-white"
                                  : theme === "dark"
                                    ? isPdf
                                      ? "text-red-200"
                                      : "text-white"
                                    : isPdf
                                      ? "text-red-900"
                                      : "text-gray-900"
                              }`}
                            >
                              {file.name}
                            </div>
                            {file.size && (
                              <div
                                className={`text-xs font-medium ${
                                  message.sender === "user"
                                    ? "text-blue-100"
                                    : theme === "dark"
                                      ? isPdf
                                        ? "text-red-300/80"
                                        : "text-gray-400"
                                      : isPdf
                                        ? "text-red-700/80"
                                        : "text-gray-600"
                                }`}
                              >
                                {formatFileSize(file.size)}
                              </div>
                            )}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                )}

                {/* Only show text if it's not just a file placeholder */}
                {message.text &&
                  !message.text.startsWith(FILE_ATTACHMENT_INDICATOR) && (
                    <div className="whitespace-pre-wrap">{message.text}</div>
                  )}
              </div>
            </div>
          );
        })}
      </div>

      <FileViewerModal
        file={selectedFile}
        isOpen={isModalOpen}
        onClose={closeModal}
        theme={theme}
      />
    </>
  );
};

export default ChatMessages;
