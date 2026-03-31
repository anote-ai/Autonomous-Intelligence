import { describe, it, expect } from "vitest";
import chatReducer, {
  chatSlice,
  clearChats,
  clearError,
  addChat,
  setChatMessages,
  evictChatMessages,
  fetchAllChats,
  deleteChat,
  renameChat,
  selectAllChats,
  selectChatsLoading,
  selectChatsError,
  selectCachedMessages,
} from "./ChatSlice";

const initialState = {
  chats: [],
  loading: false,
  error: null,
  messagesByChat: {},
};

describe("ChatSlice initial state", () => {
  it("has correct initial state shape", () => {
    const state = chatReducer(undefined, { type: "@@INIT" });
    expect(state).toEqual(initialState);
  });
});

describe("ChatSlice synchronous reducers", () => {
  it("clearChats empties chats and messagesByChat", () => {
    const populated = {
      ...initialState,
      chats: [{ id: 1, chat_name: "Test" }],
      messagesByChat: { "1": [{ id: 10 }] },
    };
    const next = chatReducer(populated, clearChats());
    expect(next.chats).toEqual([]);
    expect(next.messagesByChat).toEqual({});
  });

  it("clearError sets error to null", () => {
    const withError = { ...initialState, error: "something went wrong" };
    const next = chatReducer(withError, clearError());
    expect(next.error).toBeNull();
  });

  it("addChat prepends to chats array", () => {
    const existing = { ...initialState, chats: [{ id: 2 }] };
    const next = chatReducer(existing, addChat({ id: 1, chat_name: "New" }));
    expect(next.chats[0]).toEqual({ id: 1, chat_name: "New" });
    expect(next.chats).toHaveLength(2);
  });

  it("setChatMessages stores messages keyed by string chatId", () => {
    const next = chatReducer(
      initialState,
      setChatMessages({ chatId: 5, messages: [{ id: 99 }] })
    );
    expect(next.messagesByChat["5"]).toEqual([{ id: 99 }]);
  });

  it("evictChatMessages removes the cached entry", () => {
    const withCache = {
      ...initialState,
      messagesByChat: { "5": [{ id: 99 }], "6": [{ id: 100 }] },
    };
    const next = chatReducer(withCache, evictChatMessages(5));
    expect(next.messagesByChat["5"]).toBeUndefined();
    expect(next.messagesByChat["6"]).toBeDefined();
  });
});

describe("ChatSlice extraReducers — fetchAllChats", () => {
  it("pending sets loading=true and clears error", () => {
    const next = chatReducer(
      { ...initialState, error: "old error" },
      fetchAllChats.pending("req-id")
    );
    expect(next.loading).toBe(true);
    expect(next.error).toBeNull();
  });

  it("fulfilled sets chats and clears loading", () => {
    const chats = [{ id: 1 }, { id: 2 }];
    const next = chatReducer(
      { ...initialState, loading: true },
      fetchAllChats.fulfilled(chats, "req-id")
    );
    expect(next.loading).toBe(false);
    expect(next.chats).toEqual(chats);
    expect(next.error).toBeNull();
  });

  it("fulfilled with undefined payload defaults to empty array", () => {
    const next = chatReducer(
      initialState,
      fetchAllChats.fulfilled(undefined, "req-id")
    );
    expect(next.chats).toEqual([]);
  });

  it("rejected sets error and clears loading", () => {
    const next = chatReducer(
      { ...initialState, loading: true },
      fetchAllChats.rejected(null, "req-id", undefined, "network error")
    );
    expect(next.loading).toBe(false);
    expect(next.error).toBe("network error");
  });
});

describe("ChatSlice extraReducers — deleteChat", () => {
  const stateWithChats = {
    ...initialState,
    chats: [
      { id: 1, chat_name: "First" },
      { id: 2, chat_name: "Second" },
    ],
    messagesByChat: { "1": [], "2": [] },
  };

  it("pending sets loading=true", () => {
    const next = chatReducer(stateWithChats, deleteChat.pending("req-id"));
    expect(next.loading).toBe(true);
  });

  it("fulfilled removes the chat and its message cache", () => {
    const next = chatReducer(
      stateWithChats,
      deleteChat.fulfilled(1, "req-id")
    );
    expect(next.chats).toHaveLength(1);
    expect(next.chats[0].id).toBe(2);
    expect(next.messagesByChat["1"]).toBeUndefined();
    expect(next.messagesByChat["2"]).toBeDefined();
  });

  it("rejected sets error", () => {
    const next = chatReducer(
      stateWithChats,
      deleteChat.rejected(null, "req-id", undefined, "delete failed")
    );
    expect(next.error).toBe("delete failed");
    expect(next.loading).toBe(false);
  });
});

describe("ChatSlice extraReducers — renameChat", () => {
  const stateWithChats = {
    ...initialState,
    chats: [{ id: 3, chat_name: "Old Name" }],
  };

  it("fulfilled updates chat_name in the array", () => {
    const next = chatReducer(
      stateWithChats,
      renameChat.fulfilled({ chatId: 3, chatName: "New Name" }, "req-id")
    );
    expect(next.chats[0].chat_name).toBe("New Name");
    expect(next.error).toBeNull();
  });

  it("fulfilled is a no-op when chatId is not found", () => {
    const next = chatReducer(
      stateWithChats,
      renameChat.fulfilled({ chatId: 99, chatName: "X" }, "req-id")
    );
    expect(next.chats[0].chat_name).toBe("Old Name");
  });

  it("rejected sets error", () => {
    const next = chatReducer(
      stateWithChats,
      renameChat.rejected(null, "req-id", undefined, "rename failed")
    );
    expect(next.error).toBe("rename failed");
  });
});

describe("ChatSlice selectors", () => {
  const rootState = {
    chatReducer: {
      chats: [{ id: 1 }],
      loading: true,
      error: "err",
      messagesByChat: { "1": [{ id: 10 }] },
    },
  };

  it("selectAllChats returns chats array", () => {
    expect(selectAllChats(rootState)).toEqual([{ id: 1 }]);
  });

  it("selectChatsLoading returns loading flag", () => {
    expect(selectChatsLoading(rootState)).toBe(true);
  });

  it("selectChatsError returns error", () => {
    expect(selectChatsError(rootState)).toBe("err");
  });

  it("selectCachedMessages returns messages for chatId", () => {
    expect(selectCachedMessages(1)(rootState)).toEqual([{ id: 10 }]);
  });

  it("selectCachedMessages returns null for unknown chatId", () => {
    expect(selectCachedMessages(999)(rootState)).toBeNull();
  });

  it("selectAllChats defaults to empty array when chatReducer missing", () => {
    expect(selectAllChats({})).toEqual([]);
  });
});
