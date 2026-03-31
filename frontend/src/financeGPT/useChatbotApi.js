import { useCallback } from "react";
import fetcher from "../http/RequestConfig";

export function useChatbotApi() {
  const uploadDocuments = useCallback(async (path, formData) => {
    const response = await fetcher(path, {
      method: "POST",
      body: formData,
    });

    return response.json();
  }, []);

  const inferChatName = useCallback(async (messages, chatId) => {
    const response = await fetcher("infer-chat-name", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ messages, chat_id: chatId }),
    });

    return response.json();
  }, []);

  const retrieveMessages = useCallback(async (path, chatId, chatType = 0) => {
    const response = await fetcher(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: chatId, chat_type: chatType }),
    });

    return response.json();
  }, []);

  const retrieveCurrentDocs = useCallback(async (path, chatId) => {
    const response = await fetcher(path, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: chatId }),
    });

    return response.json();
  }, []);

  const processChatMessage = useCallback(async (path, payload, options = {}) => {
    return fetcher(path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      ...options,
    });
  }, []);

  const createChat = useCallback(async (chatType, modelType) => {
    const response = await fetcher("create-new-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_type: chatType, model_type: modelType }),
    });

    return response.json();
  }, []);

  return {
    createChat,
    inferChatName,
    processChatMessage,
    retrieveCurrentDocs,
    retrieveMessages,
    uploadDocuments,
  };
}
