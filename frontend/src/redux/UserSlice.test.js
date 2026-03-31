import {
  getAPIKeys,
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

  it("getAPIKeys.fulfilled normalizes returned keys into byId and allIds", () => {
    const populatedState = {
      ...initialState,
      entities: {
        ...initialState.entities,
        apiKeys: {
          byId: {
            99: { id: 99, key: "stale-key" },
          },
          allIds: [99],
        },
      },
    };

    const nextState = userSlice.reducer(
      populatedState,
      getAPIKeys.fulfilled(
        {
          keys: [
            { id: 2, key: "second-key", name: "Second" },
            { id: 1, key: "first-key", name: "First" },
          ],
        },
        "request-id"
      )
    );

    expect(nextState.entities.apiKeys.allIds).toEqual([2, 1]);
    expect(nextState.entities.apiKeys.byId).toEqual({
      1: { id: 1, key: "first-key", name: "First" },
      2: { id: 2, key: "second-key", name: "Second" },
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

  it("generateAPIKey.fulfilled does not add duplicate id to allIds (#74)", () => {
    // Simulate the reducer being called twice with the same key (double-dispatch /
    // stale redux-persist rehydration scenario that caused issue #74)
    const key = { id: 5, key: "sk-abc", name: "My Key" };

    const after1 = userSlice.reducer(
      initialState,
      generateAPIKey.fulfilled(key, "req-1")
    );
    const after2 = userSlice.reducer(
      after1,
      generateAPIKey.fulfilled(key, "req-2")
    );

    expect(after2.entities.apiKeys.allIds).toEqual([5]);
    expect(after2.entities.apiKeys.byId[5]).toEqual(key);
  });
});
