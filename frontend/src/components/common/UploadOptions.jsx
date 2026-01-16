import React, { useState, useRef } from "react";

const UploadOptions = ({ theme, onFileSelect, isAuthenticated }) => {
  const [showOptions, setShowOptions] = useState(false);
  const fileInputRef = useRef(null);

  const handleOptionClick = () => {
    setShowOptions(false);
    fileInputRef.current?.click();
  };

  const handleFileChange = (event, type) => {
    const files = Array.from(event.target.files || []);
    if (files.length > 0 && onFileSelect) {
      onFileSelect(files, type);
    }
    // Reset input value to allow selecting the same file again
    event.target.value = "";
  };

  const uploadOptions = [
    {
      id: 1,
      type: "file",
      label: "Add File & images",
      icon: "M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13",
      accept: "*/*",
    },
  ];

  return (
    <div className="relative">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        className="hidden"
        accept={uploadOptions[0].accept}
        onChange={(e) => handleFileChange(e, "file")}
        multiple
      />

      {/* Upload button */}
      <div className="relative group/button">
        <button
          onClick={() => isAuthenticated && setShowOptions(!showOptions)}
          disabled={!isAuthenticated}
          className={`p-2 rounded-full transition-colors ${
            isAuthenticated
              ? theme === "dark"
                ? "hover:bg-gray-600"
                : "hover:bg-gray-200"
              : "opacity-50 cursor-not-allowed"
          }`}
          aria-label="Open upload options"
        >
          <svg
            className={`w-4 h-4 ${
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

        {/* Tooltip when not authenticated */}
        {!isAuthenticated && (
          <div className="absolute bottom-full left-0 mb-2 w-48 opacity-0 group-hover/button:opacity-100 pointer-events-none transition-opacity">
            <div
              className={`text-xs px-3 py-2 rounded shadow-lg ${
                theme === "dark"
                  ? "bg-gray-800 text-gray-200"
                  : "bg-gray-50 text-black"
              }`}
            >
              Login to upload files
            </div>
          </div>
        )}
      </div>

      {/* Options dropdown */}
      {showOptions && (
        <div
          className={`absolute bottom-full left-0 mb-2 w-48 rounded-lg shadow-lg border overflow-hidden z-10 ${
            theme === "dark"
              ? "bg-gray-700 border-gray-600"
              : "bg-white border-gray-300"
          }`}
        >
          {uploadOptions.map((option) => (
            <button
              key={option.id}
              onClick={() => handleOptionClick(option.type)}
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
  );
};

export default UploadOptions;
