import React, { createContext, useContext, useState, useEffect } from "react";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useColorScheme } from "react-native";
import { lightTheme, darkTheme, Theme } from "../src/theme";
import { getToken, setToken as storeToken, clearToken } from "../src/storage";
import { setAuthToken } from "../src/api";

export const ThemeContext = createContext<{ theme: Theme; dark: boolean; toggle: () => void }>({
  theme: lightTheme,
  dark: false,
  toggle: () => {},
});

export const AuthContext = createContext<{
  token: string | null;
  login: (t: string) => Promise<void>;
  logout: () => Promise<void>;
}>({
  token: null,
  login: async () => {},
  logout: async () => {},
});

export function useAppTheme() { return useContext(ThemeContext); }
export function useAppAuth() { return useContext(AuthContext); }

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const [dark, setDark] = useState(colorScheme === "dark");
  const [token, setTokenState] = useState<string | null>(null);

  useEffect(() => {
    getToken().then((t) => {
      if (t) { setTokenState(t); setAuthToken(t); }
    });
  }, []);

  const toggle = () => setDark((d) => !d);
  const theme = dark ? darkTheme : lightTheme;

  const loginFn = async (t: string) => {
    await storeToken(t);
    setAuthToken(t);
    setTokenState(t);
  };

  const logoutFn = async () => {
    await clearToken();
    setAuthToken(null);
    setTokenState(null);
  };

  return (
    <ThemeContext.Provider value={{ theme, dark, toggle }}>
      <AuthContext.Provider value={{ token, login: loginFn, logout: logoutFn }}>
        <StatusBar style={dark ? "light" : "dark"} />
        <Stack screenOptions={{ headerShown: false }} />
      </AuthContext.Provider>
    </ThemeContext.Provider>
  );
}
