import React, { createContext, useContext, useState, useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import ChatPage from "./pages/ChatPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import LandingPage from "./landing_page/LandingPage.js";

// Theme
export const ThemeContext = createContext<{
  dark: boolean;
  toggle: () => void;
}>({ dark: false, toggle: () => {} });

// Auth
export const AuthContext = createContext<{
  token: string | null;
  setToken: (t: string | null) => void;
}>({ token: null, setToken: () => {} });

export function useTheme() { return useContext(ThemeContext); }
export function useAuth() { return useContext(AuthContext); }

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token } = useAuth();
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme");
    if (stored) return stored === "dark";
    return window.matchMedia("(prefers-color-scheme: dark)").matches;
  });

  const [token, setTokenState] = useState<string | null>(
    () => localStorage.getItem("token")
  );

  useEffect(() => {
    if (dark) document.documentElement.classList.add("dark");
    else document.documentElement.classList.remove("dark");
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  const toggle = () => setDark((d) => !d);
  const setToken = (t: string | null) => {
    setTokenState(t);
    if (t) localStorage.setItem("token", t);
    else localStorage.removeItem("token");
  };

  return (
    <ThemeContext.Provider value={{ dark, toggle }}>
      <AuthContext.Provider value={{ token, setToken }}>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/app" element={<RequireAuth><ChatPage /></RequireAuth>} />
            <Route path="/app/chat/:id" element={<RequireAuth><ChatPage /></RequireAuth>} />
          </Routes>
        </BrowserRouter>
      </AuthContext.Provider>
    </ThemeContext.Provider>
  );
}
