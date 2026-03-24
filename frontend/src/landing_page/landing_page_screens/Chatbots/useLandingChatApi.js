import { useCallback } from "react";
import fetcher from "../../../http/RequestConfig";

export function useLandingChatApi() {
  const sendMultipartChat = useCallback(async (path, formData) => {
    const response = await fetcher(path, {
      method: "POST",
      body: formData,
      isGuest: true,
    });

    return response.json();
  }, []);

  const createDemoChatFromFiles = useCallback(async (files) => {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files[]", file);
    });

    const response = await fetcher("ingest-pdf-demo", {
      method: "POST",
      body: formData,
      isGuest: true,
    });

    return response.json();
  }, []);

  const uploadDemoDocuments = useCallback(async (chatId, files) => {
    const formData = new FormData();
    Array.from(files).forEach((file) => {
      formData.append("files[]", file);
    });
    formData.append("chat_id", chatId);

    const response = await fetcher("ingest-pdf-demo", {
      method: "POST",
      body: formData,
      isGuest: true,
    });

    return response.json();
  }, []);

  return {
    createDemoChatFromFiles,
    sendMultipartChat,
    uploadDemoDocuments,
  };
}
