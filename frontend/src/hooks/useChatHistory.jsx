import { useContext } from "react";
import { ChatHistoryContext } from "../context/ChatHistoryContext";

export const useChatHistory = () => {
  const context = useContext(ChatHistoryContext);
  if (!context) {
    throw new Error("useChatHistory must be used within ChatHistoryProvider");
  }
  return context;
};
