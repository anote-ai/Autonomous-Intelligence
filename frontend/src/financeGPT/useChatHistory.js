import { useCallback, useEffect, useState } from "react";
import { post } from "../http/RequestConfig";

export function useChatHistory({ enabled = true } = {}) {
  const [chats, setChats] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refreshChats = useCallback(async () => {
    if (!enabled) {
      setChats([]);
      return;
    }
    setLoading(true);
    try {
      const response = await post("retrieve-all-chats", { chat_type: 0 });
      const responseData = await response.json();
      setChats(responseData.chat_info || []);
      setError(null);
    } catch (fetchError) {
      console.error("Error fetching chats:", fetchError);
      setError(fetchError);
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    refreshChats();
  }, [refreshChats]);

  const createChat = useCallback(async ({ chatType = 0, modelType = 0 } = {}) => {
    const response = await post("create-new-chat", {
      chat_type: chatType,
      model_type: modelType,
    });
    if (!response.ok) throw new Error("Failed to create chat");
    const data = await response.json();
    if (data.error) throw new Error(data.error);
    await refreshChats();
    return data.chat_id;
  }, [refreshChats]);

  const renameChatById = useCallback(async (chatId, chatName) => {
    const response = await post("update-chat-name", {
      chat_id: chatId,
      chat_name: chatName,
    });
    if (!response.ok) throw new Error("Failed to rename chat");
    setChats((prev) =>
      prev.map((c) => (c.id === chatId ? { ...c, chat_name: chatName } : c))
    );
  }, []);

  const deleteChatById = useCallback(async (chatId) => {
    const response = await post("delete-chat", { chat_id: chatId });
    if (!response.ok) throw new Error("Failed to delete chat");
    setChats((prev) => prev.filter((c) => c.id !== chatId));
  }, []);

  return {
    chats,
    loading,
    error,
    refreshChats,
    createChat,
    renameChatById,
    deleteChatById,
  };
}
