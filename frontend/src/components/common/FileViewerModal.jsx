import React, { useEffect, useState } from "react";

const FileViewerModal = ({ file, isOpen, onClose, theme }) => {
  const [fileContent, setFileContent] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && file) {
      loadFileContent();
    }
  }, [isOpen, file]);

  const loadFileContent = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(file.url, {
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error("Failed to load file");
      }

      const blob = await response.blob();
      const fileType = file.type || blob.type;

      // For images, create object URL
      if (fileType.startsWith("image/")) {
        setFileContent({
          type: "image",
          url: URL.createObjectURL(blob),
        });
      }
      // For text files, read as text
      else if (
        fileType.startsWith("text/") ||
        fileType === "application/json"
      ) {
        const text = await blob.text();
        setFileContent({
          type: "text",
          content: text,
        });
      }
      // For PDFs
      else if (fileType === "application/pdf") {
        setFileContent({
          type: "pdf",
          url: URL.createObjectURL(blob),
        });
      }
      // For other files, show download option
      else {
        setFileContent({
          type: "download",
          url: URL.createObjectURL(blob),
        });
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className={`max-w-5xl w-full max-h-[90vh] rounded-lg overflow-hidden ${
          theme === "dark" ? "bg-gray-800" : "bg-white"
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div
          className={`flex items-center justify-between p-4 border-b ${
            theme === "dark"
              ? "border-gray-700 bg-gray-900"
              : "border-gray-200 bg-gray-50"
          }`}
        >
          <h3
            className={`text-lg font-semibold truncate flex-1 ${
              theme === "dark" ? "text-white" : "text-gray-900"
            }`}
          >
            {file?.name}
          </h3>
          <div className="flex items-center gap-2 ml-4">
            <a
              href={file?.url}
              download={file?.name}
              className={`p-2 rounded hover:bg-opacity-80 ${
                theme === "dark"
                  ? "bg-gray-700 text-white"
                  : "bg-gray-200 text-gray-900"
              }`}
              title="Download"
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
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            </a>
            <button
              onClick={onClose}
              className={`p-2 rounded hover:bg-opacity-80 ${
                theme === "dark"
                  ? "bg-gray-700 text-white"
                  : "bg-gray-200 text-gray-900"
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
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div
          className={`p-4 overflow-auto max-h-[calc(90vh-80px)] ${
            theme === "dark" ? "bg-gray-800" : "bg-white"
          }`}
        >
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <p
                className={`text-red-500 ${
                  theme === "dark" ? "text-red-400" : "text-red-600"
                }`}
              >
                {error}
              </p>
            </div>
          )}

          {!isLoading && !error && fileContent && (
            <>
              {fileContent.type === "image" && (
                <div className="flex items-center justify-center">
                  <img
                    src={fileContent.url}
                    alt={file.name}
                    className="max-w-full h-auto"
                  />
                </div>
              )}

              {fileContent.type === "text" && (
                <pre
                  className={`whitespace-pre-wrap font-mono text-sm p-4 rounded ${
                    theme === "dark"
                      ? "bg-gray-900 text-gray-100"
                      : "bg-gray-100 text-gray-900"
                  }`}
                >
                  {fileContent.content}
                </pre>
              )}

              {fileContent.type === "pdf" && (
                <iframe
                  src={fileContent.url}
                  className="w-full h-[70vh]"
                  title={file.name}
                />
              )}

              {fileContent.type === "download" && (
                <div className="text-center py-12">
                  <svg
                    className={`w-16 h-16 mx-auto mb-4 ${
                      theme === "dark" ? "text-gray-600" : "text-gray-400"
                    }`}
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"
                    />
                  </svg>
                  <p
                    className={`mb-4 ${
                      theme === "dark" ? "text-gray-300" : "text-gray-700"
                    }`}
                  >
                    Preview not available for this file type
                  </p>
                  <a
                    href={fileContent.url}
                    download={file.name}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
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
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Download File
                  </a>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default FileViewerModal;
