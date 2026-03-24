import React from "react";
import FinanceGPTChatbot from "../../../financeGPT/components/Chatbot";

function LandingChatbot(props) {
  return (
    <FinanceGPTChatbot
      {...props}
      processMessagePath="process-message-pdf-demo"
      uploadPath="ingest-pdf-demo"
      retrieveMessagesPath="retrieve-messages-from-chat-demo"
      retrieveDocsPath="retrieve-current-docs-demo"
      enableChatNameInference={false}
      emptyStateTitle="Hello, I am your Panacea, your agentic AI assistant. What can I do to help?"
      streamResponses={false}
    />
  );
}

export default LandingChatbot;
