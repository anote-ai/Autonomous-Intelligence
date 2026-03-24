import { useCallback, useEffect, useState } from "react";
import fetcher from "../http/RequestConfig";

export function useChatHistory({ enabled = true } = {}) {
  const [chats, setChats] = useState([]);
  const [error, setError] = useState(null);

  const refreshChats = useCallback(async () => {
    if (!enabled) {
      setChats([]);
      return;
    }

    try {
      const response = await fetcher("retrieve-all-chats", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_type: 0 }),
      });

      const responseData = await response.json();
      setChats(responseData.chat_info || []);
      setError(null);
    } catch (fetchError) {
      console.error("Error fetching chats:", fetchError);
      setError(fetchError);
    }
  }, [enabled]);

  useEffect(() => {
    refreshChats();
  }, [refreshChats]);

  const renameChatById = useCallback(async (chatId, chatName) => {
    const response = await fetcher("update-chat-name", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        chat_id: chatId,
        chat_name: chatName,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to rename chat");
    }

    setChats((prevChats) =>
      prevChats.map((chat) =>
        chat.id === chatId ? { ...chat, chat_name: chatName } : chat
      )
    );
  }, []);

  const deleteChatById = useCallback(async (chatId) => {
    const response = await fetcher("delete-chat", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ chat_id: chatId }),
    });

    if (!response.ok) {
      throw new Error("Failed to delete chat");
    }

    setChats((prevChats) => prevChats.filter((chat) => chat.id !== chatId));
  }, []);

  return {
    chats,
    error,
    refreshChats,
    renameChatById,
    deleteChatById,
  };
}
