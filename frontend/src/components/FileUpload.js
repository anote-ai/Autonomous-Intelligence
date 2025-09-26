import React, { useState, useRef } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import {
  faCloudUploadAlt,
  faFile,
  faTrash,
  faCheckCircle,
  faExclamationTriangle,
  faSpinner,
} from "@fortawesome/free-solid-svg-icons";

const FileUpload = ({
  onFileSelect,
  onFileRemove,
  acceptedFileTypes = ".pdf,.doc,.docx,.txt,.csv,.xlsx,.xls",
  maxFileSize = 10 * 1024 * 1024, // 10MB default
  multiple = false,
  disabled = false,
  className = "",
  placeholder = "Click to upload or drag and drop files here",
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadStatus, setUploadStatus] = useState({}); // Track status per file
  const fileInputRef = useRef(null);

  const formatFileSize = (bytes) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const validateFile = (file) => {
    // Check file size
    if (file.size > maxFileSize) {
      return {
        valid: false,
        error: `File size exceeds ${formatFileSize(maxFileSize)} limit`,
      };
    }

    // Check file type if acceptedFileTypes is specified
    if (acceptedFileTypes) {
      const fileExtension = "." + file.name.split(".").pop().toLowerCase();
      const acceptedTypes = acceptedFileTypes.toLowerCase().split(",");
      if (!acceptedTypes.includes(fileExtension)) {
        return {
          valid: false,
          error: `File type not supported. Accepted types: ${acceptedFileTypes}`,
        };
      }
    }

    return { valid: true };
  };

  const handleFiles = (files) => {
    const fileArray = Array.from(files);
    const newFiles = [];
    const newStatus = {};

    fileArray.forEach((file) => {
      const validation = validateFile(file);
      const fileId = `${file.name}-${file.size}-${file.lastModified}`;

      if (validation.valid) {
        newFiles.push({
          id: fileId,
          file: file,
          name: file.name,
          size: file.size,
          type: file.type,
        });
        newStatus[fileId] = { status: "ready", error: null };
      } else {
        newStatus[fileId] = { status: "error", error: validation.error };
        // Still add to display list to show error
        newFiles.push({
          id: fileId,
          file: file,
          name: file.name,
          size: file.size,
          type: file.type,
        });
      }
    });

    if (multiple) {
      setUploadedFiles((prev) => [...prev, ...newFiles]);
      setUploadStatus((prev) => ({ ...prev, ...newStatus }));
    } else {
      setUploadedFiles(newFiles);
      setUploadStatus(newStatus);
    }

    // Call callback for valid files
    const validFiles = newFiles.filter(
      (f) => newStatus[f.id].status === "ready"
    );
    if (validFiles.length > 0 && onFileSelect) {
      onFileSelect(multiple ? validFiles : validFiles[0]);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFiles(e.dataTransfer.files);
    }
  };

  const handleChange = (e) => {
    e.preventDefault();
    if (disabled) return;

    if (e.target.files && e.target.files[0]) {
      handleFiles(e.target.files);
    }
  };

  const removeFile = (fileId) => {
    const fileToRemove = uploadedFiles.find((f) => f.id === fileId);
    setUploadedFiles((prev) => prev.filter((f) => f.id !== fileId));
    setUploadStatus((prev) => {
      const newStatus = { ...prev };
      delete newStatus[fileId];
      return newStatus;
    });

    if (onFileRemove && fileToRemove) {
      onFileRemove(fileToRemove);
    }
  };

  const openFileDialog = () => {
    if (!disabled && fileInputRef.current) {
      fileInputRef.current.click();
    }
  };

  const getFileIcon = (fileName) => {
    const extension = fileName.split(".").pop().toLowerCase();
    switch (extension) {
      case "pdf":
        return faFile;
      case "doc":
      case "docx":
        return faFile;
      case "txt":
        return faFile;
      case "csv":
      case "xlsx":
      case "xls":
        return faFile;
      default:
        return faFile;
    }
  };

  const getStatusIcon = (status, error) => {
    switch (status) {
      case "uploading":
        return (
          <FontAwesomeIcon
            icon={faSpinner}
            className="animate-spin text-blue-500"
          />
        );
      case "ready":
        return (
          <FontAwesomeIcon icon={faCheckCircle} className="text-green-500" />
        );
      case "error":
        return (
          <FontAwesomeIcon
            icon={faExclamationTriangle}
            className="text-red-500"
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className={`w-full ${className}`}>
      {/* Upload Area */}
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-6 transition-all duration-200 cursor-pointer
          ${
            dragActive
              ? "border-blue-400 bg-blue-50"
              : "border-gray-300 hover:border-gray-400"
          }
          ${disabled ? "opacity-50 cursor-not-allowed" : "hover:bg-gray-700"}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={acceptedFileTypes}
          onChange={handleChange}
          disabled={disabled}
          className="hidden"
        />

        <div className="text-center">
          <FontAwesomeIcon
            icon={faCloudUploadAlt}
            className={`mx-auto h-12 w-12 ${
              dragActive ? "text-blue-500" : "text-gray-400"
            }`}
          />
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-400">{placeholder}</p>
            <p className="text-xs text-gray-500 mt-1">
              {acceptedFileTypes && `Supported formats: ${acceptedFileTypes}`}
            </p>
            <p className="text-xs text-gray-500">
              Max file size: {formatFileSize(maxFileSize)}
            </p>
          </div>
        </div>
      </div>

      {/* File List */}
      {uploadedFiles.length > 0 && (
        <div className="mt-1 space-y-2">
          <h4 className="text-sm font-medium text-gray-300">
            {multiple ? "Uploaded Files:" : "Uploaded File:"}
          </h4>
          {uploadedFiles.map((file) => {
            const status = uploadStatus[file.id];
            return (
              <div
                key={file.id}
                className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border"
              >
                <div className="flex items-center space-x-3 flex-1">
                  <FontAwesomeIcon
                    icon={getFileIcon(file.name)}
                    className="text-gray-600"
                  />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    <p className="text-xs text-gray-500">
                      {formatFileSize(file.size)}
                    </p>
                    {status?.error && (
                      <p className="text-xs text-red-600 mt-1">
                        {status.error}
                      </p>
                    )}
                  </div>
                </div>

                <div className="flex items-center space-x-2">
                  {getStatusIcon(status?.status, status?.error)}
                  {!disabled && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeFile(file.id);
                      }}
                      className="text-red-500 hover:text-red-700 transition-colors"
                      title="Remove file"
                    >
                      <FontAwesomeIcon icon={faTrash} className="h-4 w-4" />
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default FileUpload;
