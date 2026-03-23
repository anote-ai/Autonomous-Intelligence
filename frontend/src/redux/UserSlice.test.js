import {
  deleteAPIKey,
  generateAPIKey,
  initialState,
  selectAPIKeys,
  userSlice,
} from "./UserSlice";

describe("UserSlice API key state", () => {
  it("selectAPIKeys returns an empty array when persisted apiKeys state is missing", () => {
    const state = {
      userReducer: {
        entities: {},
      },
    };

    expect(selectAPIKeys(state)).toEqual([]);
  });

  it("selectAPIKeys returns normalized API keys in allIds order", () => {
    const state = {
      userReducer: {
        entities: {
          apiKeys: {
            allIds: [2, 1],
            byId: {
              1: { id: 1, key: "first" },
              2: { id: 2, key: "second" },
            },
          },
        },
      },
    };

    expect(selectAPIKeys(state)).toEqual([
      { id: 2, key: "second" },
      { id: 1, key: "first" },
    ]);
  });

  it("generateAPIKey.fulfilled recreates missing apiKeys state before insert", () => {
    const stateWithoutApiKeys = {
      ...initialState,
      entities: {
        ...initialState.entities,
      },
    };
    delete stateWithoutApiKeys.entities.apiKeys;

    const nextState = userSlice.reducer(
      stateWithoutApiKeys,
      generateAPIKey.fulfilled(
        { id: 9, key: "new-key", name: "Test Key" },
        "request-id"
      )
    );

    expect(nextState.entities.apiKeys.allIds).toEqual([9]);
    expect(nextState.entities.apiKeys.byId[9]).toEqual({
      id: 9,
      key: "new-key",
      name: "Test Key",
    });
  });

  it("deleteAPIKey.fulfilled handles missing apiKeys state without throwing", () => {
    const stateWithoutApiKeys = {
      ...initialState,
      entities: {
        ...initialState.entities,
      },
    };
    delete stateWithoutApiKeys.entities.apiKeys;

    const nextState = userSlice.reducer(
      stateWithoutApiKeys,
      deleteAPIKey.fulfilled(9, "request-id")
    );

    expect(nextState.entities.apiKeys.allIds).toEqual([]);
    expect(nextState.entities.apiKeys.byId).toEqual({});
  });
});
