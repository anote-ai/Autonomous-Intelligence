import { createAsyncThunk, createSlice } from "@reduxjs/toolkit";
import fetcher from "../http/RequestConfig";
import { useSelector } from "react-redux";

export const login = createAsyncThunk("user/login", async (payload, thunk) => {
  var requestPath = "login";
  if ("email" in payload && "password" in payload) {
    requestPath +=
      "?email=" +
      encodeURIComponent(payload["email"]) +
      "&password=" +
      encodeURIComponent(payload["password"]);
  }
  if ("product_hash" in payload) {
    if ("email" in payload && "password" in payload) {
      requestPath += "&";
    } else {
      requestPath += "?";
    }
    requestPath += "product_hash=" + payload["product_hash"];
    requestPath += "&free_trial_code=" + payload["free_trial_code"];
  }
  const response = await fetcher(requestPath, {
    credentials: "include",
  });
  const response_str = await response.json();
  if ("auth_url" in response_str) {
    window.location.assign(response_str.auth_url);
  }
  return response_str;
});

export const logout = createAsyncThunk("user/logout", async (thunk) => {
  // Forget the accessToken and refreshToken
  localStorage.removeItem("accessToken");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("sessionToken");
  localStorage.removeItem("persist:root");

  // Return an empty response
  return {};
});

export const signUp = createAsyncThunk(
  "user/signUp",
  async (payload, thunk) => {
    const response = await fetcher("signUp", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const response_str = await response.json();
    return response_str;
  }
);

export const forgotPassword = createAsyncThunk(
  "user/forgotPassword",
  async (payload, thunk) => {
    const response = await fetcher("forgotPassword", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const response_str = await response.json();
    return response_str;
  }
);

export const resetPassword = createAsyncThunk(
  "user/resetPassword",
  async (payload, thunk) => {
    const response = await fetcher("resetPassword", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const response_str = await response.json();
    return response_str;
  }
);

export const generateAPIKey = createAsyncThunk(
  "user/generateAPIKey",
  async (payload, thunk) => {
    const response = await fetcher("generateAPIKey", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const response_str = await response.json();
    return response_str;
  }
);

export const deleteAPIKey = createAsyncThunk(
  "user/deleteAPIKey",
  async (id, thunk) => {
    const response = await fetcher("deleteAPIKey", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        api_key_id: id,
      }),
    });
    await response.json();
    return id;
  }
);

export const getAPIKeys = createAsyncThunk("user/getAPIKeys", async (thunk) => {
  const response = await fetcher("getAPIKeys");
  const response_str = await response.json();
  return response_str;
});

export const viewUser = createAsyncThunk("user/viewUser", async (thunk) => {
  const response = await fetcher("viewUser");
  const response_str = await response.json();
  return response_str;
});

// Gets the number of credits and refreshes it if first of the month
export const refreshCredits = createAsyncThunk(
  "user/refreshCredits",
  async (payload, thunk) => {
    const response = await fetcher("refreshCredits", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const response_str = await response.json();
    return response_str;
  }
);

// Action to deduct credits by making a server call
export const deductCreditsLocal = createAsyncThunk(
  "user/deductCreditsLocal",
  async (creditsToDeduct = 1, thunk) => {
    const response = await fetcher("deductCredits", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify({ creditsToDeduct }),
    });
    const response_str = await response.json();
    return response_str;
  }
);

export const createCheckoutSession = createAsyncThunk(
  "user/createCheckoutSession",
  async (payload, thunk) => {
    console.log(payload);
    const response = await fetcher("createCheckoutSession", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(
        `HTTP ${response.status}: ${errorData.error || "Unknown error"}`
      );
    }

    const response_str = await response.json();
    return response_str["url"];
  }
);

export const createPortalSession = createAsyncThunk(
  "user/createPortalSession",
  async (payload, thunk) => {
    const response = await fetcher("createPortalSession", {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-type": "application/json",
      },
      body: JSON.stringify(payload),
    });
    const response_str = await response.json();
    return response_str["url"];
  }
);

export function useUser() {
  return useSelector((state) => {
    try {
      return state.userReducer.entities.users.byId[
        state.userReducer.currentUser
      ];
    } catch (e) {
      return null;
    }
  });
}

export function useNumCredits() {
  return useSelector((state) => {
    return state.userReducer.numCredits;
  });
}

export function selectAPIKeys(state) {
  const apiKeysState = state?.userReducer?.entities?.apiKeys;
  const allIds = Array.isArray(apiKeysState?.allIds) ? apiKeysState.allIds : [];
  const byId =
    apiKeysState?.byId && typeof apiKeysState.byId === "object"
      ? apiKeysState.byId
      : {};

  return allIds
    .map((id) => byId[id])
    .filter((apiKey) => typeof apiKey !== "undefined");
}

export function useAPIKeys() {
  return useSelector(selectAPIKeys);
}

export function useAccessTokenIsSet() {
  return useSelector((state) => {
    return "accessToken" in state.userReducer;
  });
}
export function useRefreshTokenIsSet() {
  return useSelector((state) => {
    return "refreshToken" in state.userReducer;
  });
}
export function useAccessToken() {
  return useSelector((state) => {
    return state.userReducer.accessToken;
  });
}
export function useRefreshToken() {
  return useSelector((state) => {
    return state.userReducer.refreshToken;
  });
}

function clearUser(state) {
  state.currentUser = 0;
  state.entities.users.allIds = [];
  state.entities.users.byId = {};
}

function clearApiKeys(state) {
  if (!state.entities.apiKeys) {
    state.entities.apiKeys = { byId: {}, allIds: [] };
  }
  state.entities.apiKeys.allIds = [];
  state.entities.apiKeys.byId = {};
}

function ensureApiKeysState(state) {
  if (!state.entities) {
    state.entities = {};
  }

  if (!state.entities.apiKeys) {
    state.entities.apiKeys = { byId: {}, allIds: [] };
  }

  if (!state.entities.apiKeys.byId) {
    state.entities.apiKeys.byId = {};
  }

  if (!Array.isArray(state.entities.apiKeys.allIds)) {
    state.entities.apiKeys.allIds = [];
  }
}

export const initialState = {
  // entities holds all normalized data.
  // Initialized to be empty, but we comment the structure for documentation purposes.
  entities: {
    users: {
      byId: {
        // "user1" : {
        //     id : "user1",
        //     personName: "user name",
        //     email: "email",
        //     privilegeLevel: 0,
        // }
      },
      allIds: [
        // "user1"
      ],
    },
    apiKeys: {
      byId: {},
      allIds: [],
    },
  },
  // ID of current user.  0 is for unset.
  currentUser: 0,
  numCredits: 0,
};

export const userSlice = createSlice({
  name: "user",
  initialState: initialState,
  reducers: {
    removeAccessTokenIfExists: (state) => {
      if ("accessToken" in state) {
        delete state.accessToken;
      }
    },
    removeRefreshTokenIfExists: (state) => {
      if ("refreshToken" in state) {
        delete state.refreshToken;
      }
    },
    setAccessToken: (state, action) => {
      state.accessToken = action.payload;
    },
    setRefreshToken: (state, action) => {
      state.refreshToken = action.payload;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(refreshCredits.fulfilled, (state, action) => {
        state.numCredits = action.payload["numCredits"];
        // Also update the user object's credits field if user exists
        if (state.currentUser && state.entities.users.byId[state.currentUser]) {
          state.entities.users.byId[state.currentUser].credits =
            action.payload["numCredits"];
        }
      })
      .addCase(deductCreditsLocal.fulfilled, (state, action) => {
        // The server should return the new credit balance
        if (action.payload && action.payload.newCredits !== undefined) {
          state.numCredits = action.payload.newCredits;
          // Also update the user object's credits field if user exists
          if (
            state.currentUser &&
            state.entities.users.byId[state.currentUser]
          ) {
            state.entities.users.byId[state.currentUser].credits =
              action.payload.newCredits;
          }
        }
      })
      .addCase(viewUser.fulfilled, (state, action) => {
        clearUser(state);
        var id = action.payload["id"];
        state.currentUser = id;
        state.entities.users.allIds.push(id);
        state.entities.users.byId[id] = action.payload;
        // Sync numCredits with the credits from the user object
        if (action.payload["credits"] !== undefined) {
          state.numCredits = action.payload["credits"];
        }
      })
      .addCase(getAPIKeys.fulfilled, (state, action) => {
        clearApiKeys(state);
        var apiKeys = action.payload["keys"];
        apiKeys.forEach((apiKey) => {
          var id = apiKey["id"];
          state.entities.apiKeys.allIds.push(id);
          state.entities.apiKeys.byId[id] = apiKey;
        });
      })
      .addCase(generateAPIKey.fulfilled, (state, action) => {
        ensureApiKeysState(state);
        var payload = action.payload;
        var id = payload["id"];
        // Guard against duplicate IDs (e.g. double-dispatch or stale persisted state)
        if (!state.entities.apiKeys.allIds.includes(id)) {
          state.entities.apiKeys.allIds.push(id);
        }
        state.entities.apiKeys.byId[id] = payload;
      })
      .addCase(deleteAPIKey.fulfilled, (state, action) => {
        ensureApiKeysState(state);
        var id = action.payload;
        const index = state.entities.apiKeys.allIds.indexOf(id);
        if (index > -1) {
          // only splice array when item is found
          state.entities.apiKeys.allIds.splice(index, 1); // 2nd parameter means remove one item only
        }
        delete state.entities.apiKeys.byId[id];
      })
      .addCase(logout.fulfilled, (state, action) => {
        // Clear user data and reset credits on logout
        clearUser(state);
        clearApiKeys(state);
        state.numCredits = 0;
      });
  },
});

export const {
  removeAccessTokenIfExists,
  removeRefreshTokenIfExists,
  setAccessToken,
  setRefreshToken,
} = userSlice.actions;
