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
  lastFetchTime: null,
};

// Chat slice
export const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    clearChats: (state) => {
      state.chats = [];
    },
    clearError: (state) => {
      state.error = null;
    },
    // Add a new chat to the state (useful when creating new chats)
    addChat: (state, action) => {
      state.chats.unshift(action.payload);
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
        state.lastFetchTime = Date.now();
        state.error = null;
      })
      .addCase(fetchAllChats.rejected, (state, action) => {
        state.loading = false;
        state.error = action.payload;
      })
      // Delete chat
      .addCase(deleteChat.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(deleteChat.fulfilled, (state, action) => {
        state.loading = false;
        state.chats = state.chats.filter((chat) => chat.id !== action.payload);
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
export const { clearChats, clearError, addChat } = chatSlice.actions;

// Selectors
export const selectAllChats = (state) => state.chatReducer?.chats || [];
export const selectChatsLoading = (state) =>
  state.chatReducer?.loading || false;
export const selectChatsError = (state) => state.chatReducer?.error;
export const selectLastFetchTime = (state) => state.chatReducer?.lastFetchTime;

// Export reducer
export default chatSlice.reducer;
