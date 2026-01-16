import UploadOptions from "../common/UploadOptions";

export default function TextBox({
  theme,
  textareaRef,
  inputValue,
  handleKeyPress,
  setInputValue,
  isAuthenticated,
  handleSendMessage,
  handleFileSelect,
  uploadedFiles,
  setUploadedFiles,
  isUploading,
}) {
  return (
    <div
      className={`flex flex-col gap-2 rounded-lg border px-3 py-3 relative ${
        theme === "dark"
          ? "border-gray-600 bg-gray-700"
          : "border-gray-300 bg-gray-50"
      }`}
    >
      {/* Upload status */}
      {isUploading && (
        <div
          className={`text-sm flex items-center gap-2 ${
            theme === "dark" ? "text-gray-300" : "text-gray-600"
          }`}
        >
          <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
              fill="none"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
          <span>Uploading files...</span>
        </div>
      )}

      {/* Display uploaded files */}
      {uploadedFiles.length > 0 && (
        <div className="flex gap-2 mb-2 overflow-x-auto scrollbar-hide">
          {uploadedFiles.map((fileData) => (
            <div
              key={fileData.id}
              className={`flex items-center gap-2 px-3 py-1 rounded-full text-sm whitespace-nowrap shrink-0 ${
                theme === "dark"
                  ? "bg-gray-600 text-gray-200"
                  : "bg-gray-200 text-gray-700"
              }`}
            >
              <span className="truncate max-w-37.5">{fileData.name}</span>
              <button
                onClick={() =>
                  setUploadedFiles((prev) =>
                    prev.filter((f) => f.id !== fileData.id),
                  )
                }
                className="hover:text-red-500 transition-colors"
              >
                ×
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Input field */}
      <textarea
        ref={textareaRef}
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyPress}
        placeholder="Type your message..."
        rows={2}
        className={`bg-transparent focus:outline-none resize-none overflow-hidden ${
          theme === "dark"
            ? "text-white placeholder-gray-400"
            : "text-gray-900 placeholder-gray-500"
        }`}
      />

      {/* Action buttons */}
      <div className="flex items-center justify-between mt-2 gap-2">
        <div className="shrink-0">
          <UploadOptions
            theme={theme}
            isAuthenticated={isAuthenticated}
            onFileSelect={handleFileSelect}
          />
        </div>
        <button
          onClick={handleSendMessage}
          disabled={
            (!inputValue.trim() && uploadedFiles.length === 0) || isUploading
          }
          className="p-2 bg-teal-500 text-white rounded-full hover:bg-teal-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          aria-label="Send message"
        >
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
              d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"
            />
          </svg>
        </button>
      </div>
    </div>
  );
}
