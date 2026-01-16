import React, { useState, useEffect } from "react";
import { chatAPI } from "../../utils/api";

const ShareModal = ({ isOpen, onClose, chatUuid, chatName, theme }) => {
  const [shareLink, setShareLink] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  const generateShareLink = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await chatAPI.createShareLink(chatUuid);
      const fullLink = `${window.location.origin}/shares/${response.share_uuid}`;
      setShareLink(fullLink);
    } catch (err) {
      console.error("Error generating share link:", err);
      setError("Failed to generate share link. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen && chatUuid) {
      generateShareLink();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, chatUuid]);

  const copyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  const handleClose = () => {
    setShareLink("");
    setError(null);
    setCopied(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-100 flex items-center justify-center bg-black bg-opacity-50">
      <div
        className={`w-full max-w-md mx-4 p-6 rounded-lg shadow-xl ${
          theme === "dark" ? "bg-gray-800" : "bg-white"
        }`}
      >
        <div className="flex items-center justify-between mb-4">
          <h3
            className={`text-lg font-semibold ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            Share Chat
          </h3>
          <button
            onClick={handleClose}
            className={`p-1 rounded-full hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors`}
          >
            <svg
              className={`w-5 h-5 ${
                theme === "dark" ? "text-gray-400" : "text-gray-600"
              }`}
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

        <p
          className={`text-sm mb-4 ${
            theme === "dark" ? "text-gray-300" : "text-gray-600"
          }`}
        >
          Share "{chatName}" with others via a public link
        </p>

        {isLoading ? (
          <div className="flex justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
          </div>
        ) : error ? (
          <div className="p-4 mb-4 rounded-lg bg-red-100 dark:bg-red-900 text-red-700 dark:text-red-200 text-sm">
            {error}
          </div>
        ) : shareLink ? (
          <>
            <div
              className={`flex items-center gap-2 p-3 rounded-lg border ${
                theme === "dark"
                  ? "bg-gray-700 border-gray-600"
                  : "bg-gray-50 border-gray-300"
              }`}
            >
              <input
                type="text"
                value={shareLink}
                readOnly
                className={`flex-1 bg-transparent outline-none text-sm ${
                  theme === "dark" ? "text-gray-200" : "text-gray-700"
                }`}
              />
              <button
                onClick={copyToClipboard}
                className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  copied
                    ? "bg-green-500 text-white"
                    : theme === "dark"
                      ? "bg-gray-600 hover:bg-gray-500 text-gray-200"
                      : "bg-gray-200 hover:bg-gray-300 text-gray-700"
                }`}
              >
                {copied ? (
                  <span className="flex items-center gap-1">
                    <svg
                      className="w-4 h-4"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M5 13l4 4L19 7"
                      />
                    </svg>
                    Copied
                  </span>
                ) : (
                  "Copy"
                )}
              </button>
            </div>

            <div
              className={`mt-4 p-3 rounded-lg text-sm ${
                theme === "dark"
                  ? "bg-blue-900 text-blue-200"
                  : "bg-blue-50 text-blue-700"
              }`}
            >
              <p className="font-medium mb-1">📌 Note:</p>
              <p>Anyone with this link can view this chat conversation.</p>
            </div>
          </>
        ) : null}

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={handleClose}
            className={`px-4 py-2 rounded-lg transition-colors ${
              theme === "dark"
                ? "bg-gray-700 hover:bg-gray-600 text-gray-200"
                : "bg-gray-200 hover:bg-gray-300 text-gray-700"
            }`}
          >
            Close
          </button>
          {error && (
            <button
              onClick={generateShareLink}
              className="px-4 py-2 rounded-lg bg-blue-500 hover:bg-blue-600 text-white transition-colors"
            >
              Retry
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

export default ShareModal;
