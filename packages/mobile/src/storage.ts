import * as SecureStore from "expo-secure-store";

export async function getToken(): Promise<string | null> {
  return SecureStore.getItemAsync("auth_token");
}

export async function setToken(token: string): Promise<void> {
  await SecureStore.setItemAsync("auth_token", token);
}

export async function clearToken(): Promise<void> {
  await SecureStore.deleteItemAsync("auth_token");
}
