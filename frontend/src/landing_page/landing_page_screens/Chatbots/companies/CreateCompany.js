import React, { useState } from "react";
import Chatbot from "../../../landing_page_screens/Chatbots/Chatbot";
import { useLandingChatApi } from "../useLandingChatApi";

const CreateCompany = () => {
  const [chatId, setChatId] = useState(null);
  const { createDemoChatFromFiles } = useLandingChatApi();

  const handlePDFUploadAndCreateChat = async (e) => {
    const files = e.target.files;

    try {
      const responseData = await createDemoChatFromFiles(files);

      if (responseData.chat_id) {
        setChatId(responseData.chat_id);
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
        <Chatbot selectedChatId={chatId} />
      )}
    </div>
  );
};

export default CreateCompany;
