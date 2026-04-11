import React, { useRef, useState } from "react";
import { pdfjs } from "react-pdf";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faFileUpload } from "@fortawesome/free-solid-svg-icons";
import { useLandingChatApi } from "./useLandingChatApi";

pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`;

// print("At Anote, we offer two solutions for interacting with your documents:")
// print("1.Private Chatbot: Our 100% private chat solution ensures that no data is leaked during any stage of your conversation. However, processing may take longer as it runs locally on your machine.")
// print("2. Semi-private: This solution also provides a good level of privacy, but we use the OPENAI LLM model for enhanced query accuracy.")

// is_private = input("Please choose an option (enter 1 or 2): ")
function PDFUploader({ chat_id, handleForceUpdate }) {
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef();
  const { uploadDemoDocuments } = useLandingChatApi();

  const splashScreenStyle = {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100%",
    height: "100%",
    backgroundColor: "rgba(0, 0, 0, 0.7)",
    display: "flex",
    justifyContent: "center",
    alignItems: "center",
    fontSize: "1.5rem",
    color: "white",
    zIndex: 1000,
  };

  const uploadFile = async (e) => {
    const files = e.target.files;

    setIsUploading(true);

    try {
      await uploadDemoDocuments(chat_id, files);
      setIsUploading(false);
      handleForceUpdate();
    } catch (error) {
      console.error("Error during file upload");
      setIsUploading(false);
    }
  };

  const handleUploadBtnClick = () => {
    fileInputRef.current.click();
  };

  return (
    <div>
      {isUploading && (
        <div style={splashScreenStyle}>Processing Document...</div>
      )}
      <input
        type="file"
        style={{ display: "none" }}
        ref={fileInputRef}
        onChange={uploadFile}
        accept=".pdf, .docx, .doc, .txt, .csv"
        multiple // Allow multiple file selection
      />
      <div className="">
        <FontAwesomeIcon
          icon={faFileUpload}
          onClick={handleUploadBtnClick}
          className="px-2 text-black"
          style={{ color: "black" }}
        />
      </div>
    </div>
  );
}

export default PDFUploader;
