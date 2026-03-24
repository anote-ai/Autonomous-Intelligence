import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import fetcher from "../http/RequestConfig";

// Async thunks for chat operations
export const fetchAllChats = createAsyncThunk(
  "chat/fetchAllChats",
  async (_, { rejectWithValue }) => {
    try {
      const response = await fetcher("retrieve-all-chats", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ chat_type: 0 }),
      });

      if (!response.ok) {
        throw new Error("Failed to fetch chats");
      }

      const response_data = await response.json();
      return response_data.chat_info;
    } catch (error) {
      console.error("Error fetching chats:", error);
      return rejectWithValue(error.message);
    }
  }
);

export const deleteChat = createAsyncThunk(
  "chat/deleteChat",
  async (chatId, { rejectWithValue }) => {
    try {
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

      return chatId;
    } catch (error) {
      console.error("Error deleting chat:", error);
      return rejectWithValue(error.message);
    }
  }
);

export const renameChat = createAsyncThunk(
  "chat/renameChat",
  async ({ chatId, chatName }, { rejectWithValue }) => {
    try {
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

      return { chatId, chatName };
    } catch (error) {
      console.error("Error renaming chat:", error);
      return rejectWithValue(error.message);
    }
  }
);

// Initial state
const initialState = {
  chats: [],
  loading: false,
  error: null,
  // Per-chat message cache keyed by chatId.
  // Populated after a successful fetch so navigating back to a chat
  // renders immediately without waiting for a network round-trip.
  messagesByChat: {},
};

// Chat slice
export const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    clearChats: (state) => {
      state.chats = [];
      state.messagesByChat = {};
    },
    clearError: (state) => {
      state.error = null;
    },
    addChat: (state, action) => {
      state.chats.unshift(action.payload);
    },
    // Cache the fully-loaded message list for a chat so it can be
    // shown instantly on next visit without a loading flash.
    setChatMessages: (state, action) => {
      const { chatId, messages } = action.payload;
      state.messagesByChat[String(chatId)] = messages;
    },
    // Remove a single chat's messages from cache (e.g. after deletion).
    evictChatMessages: (state, action) => {
      delete state.messagesByChat[String(action.payload)];
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch all chats
      .addCase(fetchAllChats.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchAllChats.fulfilled, (state, action) => {
        state.loading = false;
        state.chats = action.payload || [];
        state.error = null;
      })
      .addCase(fetchAllChats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Delete chat — also evict its message cache
      .addCase(deleteChat.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteChat.fulfilled, (state, action) => {
        state.loading = false;
        state.chats = state.chats.filter((chat) => chat.id !== action.payload);
        delete state.messagesByChat[String(action.payload)];
        state.error = null;
      })
      .addCase(deleteChat.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Rename chat
      .addCase(renameChat.pending, (state) => {
        state.error = null;
      })
      .addCase(renameChat.fulfilled, (state, action) => {
        const { chatId, chatName } = action.payload;
        const chatIndex = state.chats.findIndex((chat) => chat.id === chatId);
        if (chatIndex !== -1) {
          state.chats[chatIndex].chat_name = chatName;
        }
        state.error = null;
      })
      .addCase(renameChat.rejected, (state, action) => {
        state.error = action.payload;
      });
  },
});

// Export actions
export const { clearChats, clearError, addChat, setChatMessages, evictChatMessages } = chatSlice.actions;

// Selectors
export const selectAllChats = (state) => state.chatReducer?.chats || [];
export const selectChatsLoading = (state) => state.chatReducer?.loading || false;
export const selectChatsError = (state) => state.chatReducer?.error;
export const selectCachedMessages = (chatId) => (state) =>
  state.chatReducer?.messagesByChat?.[String(chatId)] ?? null;

// Export reducer
export default chatSlice.reducer;
