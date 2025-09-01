import React, { useState, useRef, useEffect } from "react";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faPaperPlane, faUndoAlt } from "@fortawesome/free-solid-svg-icons";
import PDFUploader from "../../../landing_page_screens/Chatbots/PdfUploader";
import Chatbot from "../../../landing_page_screens/Chatbots/Chatbot";
import fetcher from "../../../../http/RequestConfig";

const CreateCompany = () => {
  const [chatId, setChatId] = useState(null);
  const [forceUpdateFlag, setForceUpdateFlag] = useState(false);

  const handleForceUpdate = () => {
    // This is passed to PDFUploader to trigger re-rendering if needed
    setForceUpdateFlag(!forceUpdateFlag);
  };

  const handlePDFUploadAndCreateChat = async (e) => {
    const files = e.target.files;

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
      formData.append("files[]", files[i]);
    }

    try {
      // Create chatbot & ingest PDF
      const response = await fetcher("ingest-pdf-demo", {
        method: "POST",
        body: formData,
      });

      const responseData = await response.json();

      if (responseData.chat_id) {
        setChatId(responseData.chat_id);
        handleForceUpdate(); // trigger Chatbot update if needed
      }
    } catch (error) {
      console.error("Failed to create chat from PDF:", error);
    }
  };

  return (
    <div className="text-white p-6">
      {!chatId ? (
        <>
          <h2 className="text-xl mb-4">Upload a PDF to Create a Company Chatbot</h2>
          <input
            type="file"
            accept=".pdf,.docx,.doc,.txt,.csv"
            multiple
            onChange={handlePDFUploadAndCreateChat}
            className="block w-full text-sm text-gray-500
              file:mr-4 file:py-2 file:px-4
              file:rounded-full file:border-0
              file:text-sm file:font-semibold
              file:bg-blue-50 file:text-blue-700
              hover:file:bg-blue-100
            "
          />
        </>
      ) : (
        <Chatbot selectedChatId={chatId} handleForceUpdate={handleForceUpdate} />
      )}
    </div>
  );
};

export default CreateCompany;
