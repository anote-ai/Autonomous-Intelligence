import { useNavigate } from "react-router-dom";
import React, {
  useState,
  useEffect,
  useRef,
  forwardRef,
  useImperativeHandle,
} from "react";
import fetcher from "../../http/RequestConfig";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faTrashCan } from "@fortawesome/free-solid-svg-icons";
import { faEye } from "@fortawesome/free-solid-svg-icons";

import Sources from "./Sources";
import ChatHistory from "./ChatHistory";
import Select from "react-select";
import { SelectStyles } from "../../styles/SelectStyles";
import { Modal } from "flowbite-react";
import { FaDatabase } from "react-icons/fa";
import { connectorOptions } from "../../constants/RouteConstants";

const SidebarChatbot = forwardRef((props, ref) => {
  const [docs, setDocs] = useState([]);
  const [showConfirmPopup, setShowConfirmPopup] = useState(false);

  const [showConfirmModelKey, setShowConfirmModelKey] = useState(false);
  const [showErrorKeyMessage, setShowErrorKeyMesage] = useState(false);
  const [showConfirmResetKey, setShowConfirmResetKey] = useState(false);
  const [pendingModel, setPendingModel] = useState(props.isPrivate);
  const [modelKey, setModelKey] = useState("");

  const [showConfirmPopupDoc, setShowConfirmPopupDoc] = useState(false);
  const [docToDeleteName, setDocToDeleteName] = useState(null);
  const [docToDeleteId, setDocToDeleteId] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedTaskType, setSelectedTaskType] = useState("");

  // Upload-related state
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const fileInputRef = useRef(null);
  const [fileModalOpen, setFileModalOpen] = useState(false);
  const [currentFile, setCurrentFile] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [loadingFile, setLoadingFile] = useState(false);

  // Expose openFileDialog method to parent components
  useImperativeHandle(ref, () => ({
    openFileDialog,
  }));

  const urlObject = new URL(window.location.origin);

  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  useEffect(() => {
    retrieveDocs();
  }, [props.selectedChatId, props.forceUpdate]);

  useEffect(() => {
    console.log("test");
    //changeChatMode(props.isPrivate);
    props.handleForceUpdate();
  }, [props.isPrivate]);

  useEffect(() => {
    setModelKey(props.confirmedModelKey);
    props.handleForceUpdate();
  }, [props.confirmedModelKey]);

  // Handle upload trigger from chatbot
  useEffect(() => {
    if (props.triggerUpload) {
      openFileDialog();
      props.resetUploadTrigger();
    }
  }, [props.triggerUpload]);

  // Poll for chat readiness
  const pollForChatReady = async (
    chatId,
    maxAttempts = 10,
    interval = 1500
  ) => {
    let attempts = 0;
    while (attempts < maxAttempts) {
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
        if (data && (data.messages?.length > 0 || data.chat_name)) {
          return true;
        }
      } catch (err) {
        // ignore errors, just retry
      }
      await new Promise((resolve) => setTimeout(resolve, interval));
    }
    return false;
  };

  // File upload handlers
  const handleFileSelect = async (event) => {
    console.log("File selection event triggered");
    const files = Array.from(event.target.files);
    console.log("Files selected:", files);

    if (files.length === 0) {
      return;
    }

    let chatId = props.selectedChatId;
    // If no chat is selected, create a new chat first
    if (!chatId && props.createNewChat) {
      try {
        chatId = await props.createNewChat();
      } catch (err) {
        alert("Failed to create a new chat. Please try again.");
        return;
      }
    }

    // Add new files to existing selection
    const newFiles = [...selectedFiles, ...files];
    setSelectedFiles(newFiles);
    console.log("Updated selected files:", newFiles);

    // Clear the input value so the same file can be selected again if needed
    event.target.value = "";

    // Automatically upload the newly selected files
    try {
      await handleFileUpload(files, chatId);
      console.log("Files uploaded successfully");
      // Poll for chat readiness and trigger redirect if ready
      if (chatId && props.onChatReady) {
        const ready = await pollForChatReady(chatId);
        if (ready) {
          props.onChatReady(chatId);
        }
      }
    } catch (error) {
      console.error("Auto-upload failed:", error);
      alert("Failed to upload files. Please try again.");
      // Remove the files that failed to upload from selectedFiles
      setSelectedFiles((prev) => prev.filter((file) => !files.includes(file)));
    }
  };

  // Reset file viewer when no files are selected
  React.useEffect(() => {
    if (selectedFiles.length === 0) {
      // Files cleared, no additional state to reset
    }
  }, [selectedFiles.length]);

  const handleFileUpload = async (
    filesToUpload = selectedFiles,
    chatId = props.selectedChatId
  ) => {
    console.log("Upload button clicked!");
    console.log("Files to upload:", filesToUpload);
    console.log("Chat ID:", chatId);
    console.log("Selected Chat ID from props:", props.selectedChatId);

    if (filesToUpload.length === 0) {
      console.log("No files selected");
      return null;
    }

    if (!chatId) {
      console.log("No chat ID available");
      alert("Please select or create a chat first before uploading files.");
      return null;
    }

    setIsUploading(true);
    setUploadProgress(0);

    // Update parent state
    if (props.setIsUploading) props.setIsUploading(true);
    if (props.setUploadProgress) props.setUploadProgress(0);

    try {
      const formData = new FormData();
      // Use the same format as the backend expects: files[]
      filesToUpload.forEach((file) => {
        formData.append("files[]", file);
      });
      formData.append("chat_id", chatId);

      // Use XMLHttpRequest for real progress tracking with correct endpoint
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const progress = Math.round((event.loaded * 100) / event.total);
            setUploadProgress(progress);
            // Update parent state
            if (props.setUploadProgress) props.setUploadProgress(progress);
          }
        };

        xhr.onload = () => {
          if (xhr.status === 200) {
            try {
              // We don't need to parse the result since we're not using it
              setIsUploading(false);
              setUploadProgress(100);

              // Update parent state
              if (props.setIsUploading) props.setIsUploading(false);
              if (props.setUploadProgress) props.setUploadProgress(100);

              // Clear progress after a short delay
              setTimeout(() => {
                setUploadProgress(0);
                if (props.setUploadProgress) props.setUploadProgress(0);
              }, 1000);

              // Return file info for display in chat
              const uploadedFiles = filesToUpload.map((file, index) => ({
                name: file.name,
                size: file.size,
                type: file.type,
                id: `uploaded-${Date.now()}-${index}`,
              }));

              // Auto-refresh documents list after successful upload
              setTimeout(() => {
                if (props.selectedChatId) {
                  retrieveDocs();
                }
              }, 500);

              // Clear selected files after successful upload
              setSelectedFiles([]);

              resolve(uploadedFiles);
            } catch (e) {
              setIsUploading(false);
              setUploadProgress(0);
              // Update parent state
              if (props.setIsUploading) props.setIsUploading(false);
              if (props.setUploadProgress) props.setUploadProgress(0);
              reject(new Error("Invalid response format"));
            }
          } else {
            setIsUploading(false);
            setUploadProgress(0);
            // Update parent state
            if (props.setIsUploading) props.setIsUploading(false);
            if (props.setUploadProgress) props.setUploadProgress(0);
            reject(new Error(`Upload failed with status: ${xhr.status}`));
          }
        };

        xhr.onerror = () => {
          setIsUploading(false);
          setUploadProgress(0);
          // Update parent state
          if (props.setIsUploading) props.setIsUploading(false);
          if (props.setUploadProgress) props.setUploadProgress(0);
          reject(new Error("Network error during upload"));
        };

        // Use the existing ingest-pdf endpoint
        xhr.open(
          "POST",
          `${process.env.REACT_APP_BACK_END_HOST || ""}/ingest-pdf`
        );

        // Add authentication headers using the same pattern as fetcher
        const accessToken = localStorage.getItem("accessToken");
        const sessionToken = localStorage.getItem("sessionToken");

        if (accessToken) {
          xhr.setRequestHeader("Authorization", `Bearer ${accessToken}`);
        } else if (sessionToken) {
          xhr.setRequestHeader("Authorization", `Bearer ${sessionToken}`);
        }

        xhr.send(formData);
      });
    } catch (error) {
      console.error("File upload error:", error);
      setIsUploading(false);
      setUploadProgress(0);
      // Update parent state
      if (props.setIsUploading) props.setIsUploading(false);
      if (props.setUploadProgress) props.setUploadProgress(0);
      throw error; // Re-throw to handle in calling function
    }
  };

  const openFileDialog = () => {
    if (fileInputRef.current) {
      // Try multiple approaches to ensure the file dialog opens
      try {
        // Method 1: Direct click
        fileInputRef.current.click();
      } catch (error) {
        console.error("Direct click failed:", error);

        // Method 2: Dispatch click event
        try {
          const clickEvent = new MouseEvent("click", {
            bubbles: true,
            cancelable: true,
            view: window,
          });
          fileInputRef.current.dispatchEvent(clickEvent);
        } catch (dispatchError) {
          console.error("Event dispatch failed:", dispatchError);
        }
      }
    } else {
      console.error("File input ref is null!");
    }
  };

  // Handle viewing uploaded documents
  const handleViewUploadedDoc = async (doc) => {
    try {
      setCurrentFile(doc);
      setFileModalOpen(true);
      setLoadingFile(true);
      setFileContent(null);

      // Try to fetch actual document content
      try {
        const response = await fetcher("get-doc-content", {
          method: "POST",
          headers: {
            Accept: "application/json",
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            doc_id: doc.doc_id,
          }),
        });

        if (response.ok) {
          const docData = await response.json();
          setFileContent({
            type: "document-content",
            name: docData.document_name,
            content: docData.document_text,
            uploadDate: doc.upload_date,
            docId: doc.doc_id,
            isUploaded: true,
          });
        } else {
          // Fallback to document info if content fetch fails
          setFileContent({
            type: "document-info",
            name: doc.doc_name,
            uploadDate: doc.upload_date,
            docId: doc.doc_id,
            isUploaded: true,
            error: "Could not load document content",
          });
        }
      } catch (contentError) {
        console.error("Error fetching document content:", contentError);
        // Fallback to document info
        setFileContent({
          type: "document-info",
          name: doc.doc_name,
          uploadDate: doc.upload_date,
          docId: doc.doc_id,
          isUploaded: true,
          error: "Could not load document content",
        });
      }

      setLoadingFile(false);
    } catch (error) {
      console.error("Error viewing uploaded document:", error);
      setLoadingFile(false);
      setFileContent({ error: "Error loading document" });
    }
  };

  // Clean up blob URLs when modal closes
  const closeModal = () => {
    if (fileContent?.isLocal && fileContent?.url) {
      URL.revokeObjectURL(fileContent.url);
    }
    setFileModalOpen(false);
    setCurrentFile(null);
    setFileContent(null);
  };

  {
    /* Delete doc section */
  }
  const handleDeleteDoc = async (doc_name, doc_id) => {
    setDocToDeleteName(doc_name);
    setDocToDeleteId(doc_id);
    setShowConfirmPopupDoc(true);
  };

  const confirmDeleteDoc = () => {
    console.log("Deleting document:", docToDeleteName);

    deleteDoc(docToDeleteId);
    setShowConfirmPopupDoc(false);
  };

  const cancelDeleteDoc = () => {
    setShowConfirmPopupDoc(false);
  };

  {
    /* Delete chat section */
  }
  const handleModelKey = async () => {
    console.log("is private", props.isPrivate);
    //setChatIdToRename(chat_id);
    if (props.isPrivate === 1) {
      console.log("cow");
      setShowErrorKeyMesage(true);
    } else {
      setShowConfirmModelKey(true);
    }
  };

  const confirmModelKey = () => {
    resetChat();
    props.setConfirmedModelKey(modelKey);
    addModelKeyToDb(modelKey);
    setShowConfirmModelKey(false);
  };

  const cancelModelKey = () => {
    setShowConfirmModelKey(false);
  };

  const cancelErrorKeyMessage = () => {
    setShowErrorKeyMesage(false);
  };

  const handleResetModel = () => {
    setShowConfirmResetKey(true);
  };

  const confirmResetModel = () => {
    console.log("i am here");
    resetChat();
    addModelKeyToDb(null);
    props.setConfirmedModelKey("");
    setShowConfirmResetKey(false);
  };

  const cancelResetModel = () => {
    setShowConfirmResetKey(false);
  };

  const addModelKeyToDb = async (model_key_db) => {
    const response = await fetcher("add-model-key", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: props.selectedChatId,
        model_key: model_key_db,
      }),
    });
    props.handleForceUpdate();
  };

  const resetChat = async () => {
    const response = await fetcher("reset-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: props.selectedChatId,
        delete_docs: false,
      }),
    });
    props.handleForceUpdate();
  };

  const changeChatMode = async (isPrivate) => {
    const response = await fetcher("change-chat-mode", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: props.selectedChatId,
        model_type: isPrivate,
      }), //model_type=1 when private, model_type=0 when public
    })
      .then((response) => {
        console.log("Chat mode changed successfully");

        //props.handleForceUpdate();
      })
      .catch((e) => {
        console.error(e.error);
      });

    props.handleForceUpdate();
  };

  const retrieveDocs = async () => {
    const response = await fetcher("retrieve-current-docs", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: props.selectedChatId }),
    }).catch((e) => {
      console.error(e.error);
    });

    const response_data = await response.json();
    setDocs(response_data.doc_info);
  };

  const deleteDoc = async (doc_id) => {
    const response = await fetcher("delete-doc", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ doc_id: doc_id }),
    }).catch((e) => {
      console.error(e.error);
    });
    props.handleForceUpdate(); //to force it to update
  };

  const deleteConfirmationPopupDoc = showConfirmPopupDoc ? (
    <div
      style={{
        position: "absolute",
        zIndex: 1000,
        color: "black",
        background: "white",
        padding: 20,
        borderRadius: 5,
        boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
      }}
    >
      <p>Are you sure you want to delete {docToDeleteName}?</p>
      <button
        onClick={confirmDeleteDoc}
        className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
      >
        Yes
      </button>
      <button
        onClick={cancelDeleteDoc}
        className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400"
      >
        No
      </button>
    </div>
  ) : null;
  const handleSwitchChange = () => {
    setShowConfirmPopup(true);
  };

  const confirmSwitchChange = () => {
    props.setIsPrivate((prevState) => 1 - prevState); //toggle true or false
    changeChatMode(props.isPrivate);
    setShowConfirmPopup(false);
  };

  const cancelSwitchChange = () => {
    setShowConfirmPopup(false);
  };

  const confirmPopup = showConfirmPopup ? (
    <div
      style={{
        position: "fixed",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        zIndex: 1000,
        padding: 20,
        borderRadius: 5,
        boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
        textAlign: "center",
      }}
      className="bg-[#141414]
 text-white"
    >
      <p>
        Warning: You are changing the chat mode. This will reset your current
        chat and delete its history. Are you sure you want to proceed?
      </p>
      <div className="w-full flex justify-between mt-4">
        <button
          onClick={confirmSwitchChange}
          className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
"
        >
          Yes
        </button>
        <button
          onClick={cancelSwitchChange}
          className="w-1/2 mx-2 py-2 bg-gray-700 rounded-lg hover:bg-[#141414]
"
        >
          No
        </button>
      </div>
    </div>
  ) : null;

  const confirmModelPopup = showConfirmModelKey ? (
    <>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)", // Semi-transparent black
          zIndex: 999, // Ensure it's below the modal but above everything else
        }}
      ></div>
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          color: "black",
          backgroundColor: "white",
          padding: 20,
          borderRadius: 5,
          boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
          textAlign: "center",
        }}
      >
        <p>
          Warning: You are changing the OpenAI fine tuning model. This will
          reset your current chat and delete its history. Are you sure you want
          to proceed?
        </p>
        <button
          onClick={confirmModelKey}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
        >
          Yes
        </button>
        <button
          onClick={cancelModelKey}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400"
        >
          No
        </button>
      </div>
    </>
  ) : null;

  const confirmResetModelPopup = showConfirmResetKey ? (
    <>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)", // Semi-transparent black
          zIndex: 999, // Ensure it's below the modal but above everything else
        }}
      ></div>
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          color: "black",
          backgroundColor: "white",
          padding: 20,
          borderRadius: 5,
          boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
          textAlign: "center",
        }}
      >
        <p>
          Warning: You are resetting the OpenAI fine tuning model. This will
          reset your current chat and delete its history. Are you sure you want
          to proceed?
        </p>
        <button
          onClick={confirmResetModel}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
        >
          Yes
        </button>
        <button
          onClick={cancelResetModel}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400"
        >
          No
        </button>
      </div>
    </>
  ) : null;

  const errorKeyPopup = showErrorKeyMessage ? (
    <>
      <div
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)", // Semi-transparent black
          zIndex: 999, // Ensure it's below the modal but above everything else
        }}
      ></div>
      <div
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          zIndex: 1000,
          color: "black",
          backgroundColor: "white",
          padding: 20,
          borderRadius: 5,
          boxShadow: "0px 0px 15px rgba(0,0,0,0.5)",
          textAlign: "center",
        }}
      >
        <p>
          You cannot add your own fine-tuned model key when you are in private
          mode
        </p>
        <button
          onClick={cancelErrorKeyMessage}
          className="p-2 my-1 bg-gray-600 rounded-lg hover:bg-gray-400 mr-5"
        >
          Close
        </button>
      </div>
    </>
  ) : null;

  const overlayStyle = {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(0, 0, 0, 0.5)",
    zIndex: 999, // Ensure it's below the popup but above everything else
  };

  var modelOptions = [];
  modelOptions.push(
    { value: 0, label: "OpenAI" },
    { value: 1, label: "Claude" }
  );

  const taskoptions = [
    { value: 0, label: "File Uploader" },
    { value: 1, label: "10-K Edgar" },
  ];

  // Function to handle when an option is selected
  const handleChange = (selectedOption) => {
    props.setcurrTask(selectedOption.value);
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleDatasetSelect = async (datasetName) => {
    // navigate to the filePath
    handleCloseModal(); // Close the modal after download
  };

  const filteredOptions = connectorOptions.filter(
    (option) => selectedTaskType === "" || option.taskType === selectedTaskType
  );

  const onConnectorCardClick = (value) => {
    handleDatasetSelect(value);
  };

  // Determine the current selected value based on props.currTask
  const selectedTaskValue = taskoptions.find(
    (option) => option.value === props.currTask
  );

  // Extract unique cited files from messages
  const citedFiles = React.useMemo(() => {
    const files = {};
    (props.messages || []).forEach((msg) => {
      if (Array.isArray(msg.relevant_chunks)) {
        msg.relevant_chunks.forEach((chunk) => {
          const key = chunk.document_name || chunk.filename;
          if (key) files[key] = chunk;
        });
      }
    });
    return Object.values(files);
  }, [props.messages]);

  return (
    <>
      <div className="flex flex-col py-4 mt-12 bg-anoteblack-800 text-white">
        {deleteConfirmationPopupDoc}
        <div className="flex flex-col flex-grow">
          <div className="bg-[#141414] rounded-xl">
            <h2 className="text-[#9C9C9C] uppercase tracking-wide font-semibold text-xs pt-2 px-4">
              Model Selection
            </h2>
            {showConfirmPopup && <div style={overlayStyle}></div>}
            {confirmPopup}
            {errorKeyPopup}
            {confirmModelPopup}
            {confirmResetModelPopup}
            <div className="rounded py-3 mx-4">
              <div className="flex-1 bg-[#141414] rounded-xl">
                <ul className="">
                  <Select
                    name="publicOptions"
                    id="publicOptions"
                    className="bg-[#3A3B41] rounded-lg focus:ring-0 hover:ring-0 hover:border-white border-none text-white cursor-pointer"
                    onChange={handleSwitchChange}
                    options={modelOptions}
                    styles={SelectStyles}
                    isSearchable={false}
                    // value={props.isPrivate === 0 ? "OpenAI" : "Claude"}
                  ></Select>
                </ul>
              </div>
            </div>
            <div className="">
              {props.confirmedModelKey && (
                <button
                  class="bg-gray-700 hover:bg-gray-600 text-white font-bold py-1 px-2 rounded ml-4 mt-3 text-sm"
                  onClick={handleResetModel}
                >
                  Reset model key
                </button>
              )}
            </div>
          </div>
          <div className="flex flex-col px-4 mt-4">
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-[#FFFFFF] uppercase tracking-wide font-semibold text-s">
                Uploaded Files
              </h2>
            </div>

            {/* Show message when no chat is selected */}
            {!props.selectedChatId && (
              <div className="mb-2 text-xs text-yellow-400">
                Please select or create a chat to view files
              </div>
            )}

            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileSelect}
              multiple
              accept="image/*,.pdf,.doc,.docx,.txt"
              style={{
                position: "absolute",
                left: "-9999px",
                opacity: 0,
                pointerEvents: "none",
              }}
            />

            {/* Map through docs */}
            <div className="bg-anoteblack-900 rounded-xl border border-gray-600 h-48 overflow-y-auto">
              {docs.map((doc) => (
                <div
                  key={doc.document_name}
                  className="flex items-center justify-between mx-4 my-2 bg-[#7E7E7E]/10 hover:bg-[#3A3B41] rounded-xl overflow-x-scroll"
                >
                  <button
                    key={doc.document_name}
                    className="flex items-center p-2 my-1 rounded-lg"
                    onClick={() => handleViewUploadedDoc(doc)}
                    title="Click to view document"
                  >
                    <span className="text-lg">📄</span>{" "}
                    {/* Replace with actual icon */}
                    <span className="ml-2">{doc.document_name}</span>
                  </button>
                  <button
                    onClick={() => handleDeleteDoc(doc.document_name, doc.id)}
                    className="p-2 ml-4 rounded-full "
                  >
                    <FontAwesomeIcon icon={faTrashCan} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Chat History Section */}
      <div className="border-t border-gray-700 pt-4">
        <div className="px-2">
          <ChatHistory
            chats={props.chats}
            selectedChatId={props.selectedChatId}
            onChatSelect={props.onChatSelect}
            handleForceUpdate={props.handleForceUpdate}
          />
        </div>
      </div>

      <div className="overflow-y-auto border-t border-gray-700 pt-4">

      </div>
      {isModalOpen && (
        <Modal
          size="3xl"
          show={isModalOpen}
          onClose={handleCloseModal}
          theme={{
            root: {
              show: {
                on: "flex bg-[#141414] bg-opacity-50 dark:bg-opacity-80",
              },
            },
            content: {
              base: "relative h-full w-full p-4 md:h-auto",
              inner:
                "relative rounded-lg shadow bg-gray-950 flex flex-col max-h-[90vh] text-white",
            },
          }}
        >
          <Modal.Header className="border-b border-gray-600 pb-1 text-center">
            <div className="flex justify-center items-center w-full text-center">
              <h2 className="font-bold text-xl text-center text-white ml-[70vh]">
                Organization Chatbots
              </h2>
            </div>
          </Modal.Header>
          <Modal.Body className="w-full overflow-y-auto">
            <div className="text-center mb-4 text-sm">
              Supported organization datasets include enterprise or individual
              fine tuned chatbots.
            </div>

            <div className="flex justify-center space-x-4 mb-6">
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === "Classification"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("Organization")}
              >
                Organization
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === "Chatbot"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("Individual")}
              >
                Individual
              </button>
              <button
                className={`px-4 py-2 rounded-lg transition-all duration-300 transform hover:scale-105 ${
                  selectedTaskType === ""
                    ? "bg-blue-600 text-white"
                    : "bg-gray-600 text-gray-200 hover:bg-gray-500"
                }`}
                onClick={() => setSelectedTaskType("")}
              >
                All
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
              {filteredOptions.map((option, index) => (
                <div
                  key={index}
                  className={`p-4 border rounded-lg shadow-md cursor-pointer transition-all duration-300 hover:shadow-xl bg-gray-700 text-gray-200 hover:bg-gray-600
                    }`}
                  onClick={() => onConnectorCardClick(option.value)}
                >
                  <div className="flex flex-col items-center text-center">
                    <FaDatabase className="mb-2" size={20} />
                    <div className="text-sm font-semibold mb-1">
                      {option.label}
                    </div>
                    <div className="text-xs text-gray-300">
                      {option.taskType}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Modal.Body>
        </Modal>
      )}

      {/* File Modal */}
      {fileModalOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75"
          onClick={closeModal}
        >
          <div
            className="bg-white rounded-lg max-w-4xl max-h-[90vh] w-full mx-4 flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-center justify-between p-4 border-b">
              <h3 className="text-lg font-semibold truncate text-black">
                {currentFile?.name || currentFile?.filename || "File Preview"}
                {fileContent?.isLocal && (
                  <span className="text-sm text-gray-500 ml-2">
                    (Local File)
                  </span>
                )}
              </h3>
              <button
                onClick={closeModal}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ✕
              </button>
            </div>

            {/* Modal Content */}
            <div className="flex-1 p-4 overflow-auto">
              {loadingFile ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-gray-500">Loading file...</div>
                </div>
              ) : fileContent?.error ? (
                <div className="flex items-center justify-center h-32">
                  <div className="text-red-500">{fileContent.error}</div>
                </div>
              ) : fileContent?.type === "image" ? (
                <div className="flex justify-center">
                  <img
                    src={fileContent.url}
                    alt={fileContent.name}
                    className="max-w-full max-h-[60vh] object-contain"
                  />
                </div>
              ) : fileContent?.type === "pdf" ? (
                <iframe
                  src={fileContent.url}
                  className="w-full h-[60vh] border-0"
                  title={fileContent.name}
                />
              ) : fileContent?.type === "text" ? (
                <div className="bg-gray-50 p-4 rounded border">
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 max-h-[50vh] overflow-auto">
                    {fileContent.content}
                  </pre>
                </div>
              ) : fileContent?.type === "download" ? (
                <div className="flex flex-col items-center justify-center h-32 space-y-4">
                  <div className="text-gray-600 text-center">
                    <div className="text-2xl mb-2">📄</div>
                    <div>
                      {fileContent.isLocal
                        ? "File ready for upload"
                        : "Preview not available for this file type"}
                    </div>
                    <div className="text-sm text-gray-500">
                      {fileContent.name}
                    </div>
                    {fileContent.isLocal && fileContent.size && (
                      <div className="text-xs text-gray-400 mt-1">
                        Size: {(fileContent.size / 1024 / 1024).toFixed(2)} MB
                        {fileContent.lastModified && (
                          <span className="ml-2">
                            Modified:{" "}
                            {new Date(
                              fileContent.lastModified
                            ).toLocaleDateString()}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                  {!fileContent.isLocal && (
                    <button
                      onClick={() => window.open(fileContent.url, "_blank")}
                      className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600 transition-colors"
                    >
                      Download File
                    </button>
                  )}
                </div>
              ) : fileContent?.type === "document-info" ? (
                <div className="flex flex-col items-center justify-center h-64 space-y-4">
                  <div className="text-gray-600 text-center">
                    <div className="text-4xl mb-4">📄</div>
                    <div className="text-lg font-medium text-gray-800 mb-2">
                      Uploaded Document
                    </div>
                    <div className="text-sm text-gray-500 mb-4">
                      {fileContent.name}
                    </div>

                    <div className="bg-gray-50 p-4 rounded-lg border space-y-2 text-left max-w-md">
                      <div className="flex justify-between">
                        <span className="font-medium">Document ID:</span>
                        <span className="text-gray-600">
                          {fileContent.docId}
                        </span>
                      </div>
                      {fileContent.uploadDate && (
                        <div className="flex justify-between">
                          <span className="font-medium">Upload Date:</span>
                          <span className="text-gray-600">
                            {new Date(
                              fileContent.uploadDate
                            ).toLocaleDateString()}
                          </span>
                        </div>
                      )}
                      <div className="flex justify-between">
                        <span className="font-medium">Status:</span>
                        <span className="text-green-600">✓ Processed</span>
                      </div>
                    </div>

                    <div className="text-xs text-gray-400 mt-4">
                      This document has been uploaded and processed for
                      chatting. The content is available for questions and
                      analysis.
                    </div>
                  </div>
                </div>
              ) : fileContent?.type === "document-content" ? (
                <div className="bg-gray-50 p-4 rounded border">
                  <div className="text-sm font-medium text-gray-800 mb-2">
                    Document Content:
                  </div>
                  <pre className="whitespace-pre-wrap text-sm text-gray-800 max-h-[50vh] overflow-auto">
                    {fileContent.content}
                  </pre>
                </div>
              ) : (
                <div className="flex items-center justify-center h-32">
                  <div className="text-gray-500">Unable to load file</div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            {fileContent && !fileContent.error && (
              <div className="border-t p-4 flex justify-between items-center">
                <div className="text-sm text-gray-500">
                  {fileContent.name}
                  {fileContent.isLocal && (
                    <span className="ml-2 text-blue-500">
                      (Ready to upload)
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  {fileContent.url && !fileContent.isLocal && (
                    <>
                      <button
                        onClick={() => window.open(fileContent.url, "_blank")}
                        className="text-blue-500 hover:text-blue-700 text-sm"
                      >
                        Open in New Tab
                      </button>
                      <button
                        onClick={() => {
                          const link = document.createElement("a");
                          link.href = fileContent.url;
                          link.download = fileContent.name || "download";
                          link.click();
                        }}
                        className="text-blue-500 hover:text-blue-700 text-sm"
                      >
                        Download
                      </button>
                    </>
                  )}
                  {fileContent.isLocal && (
                    <span className="text-xs text-gray-400">
                      File will be uploaded when you click the Upload button
                    </span>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
});

export default SidebarChatbot;
