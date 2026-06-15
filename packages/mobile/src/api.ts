import axios from "axios";
import { API_BASE } from "./constants";

export const api = axios.create({ baseURL: API_BASE });

export function setAuthToken(token: string | null) {
  if (token) api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  else delete api.defaults.headers.common["Authorization"];
}

export interface Session {
  id: string;
  title: string;
  createdAt: string;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
}

export async function login(email: string, password: string) {
  const res = await api.post("/auth/login", { email, password });
  return res.data.access_token as string;
}

export async function register(email: string, password: string, name: string) {
  const res = await api.post("/auth/register", { email, password, name });
  return res.data.access_token as string;
}

export async function getSessions(): Promise<Session[]> {
  const res = await api.get("/api/chat/sessions");
  return res.data.sessions ?? [];
}

export async function getSession(id: string): Promise<Message[]> {
  const res = await api.get(`/api/chat/sessions/${id}`);
  return res.data.messages ?? [];
}

export async function deleteSession(id: string): Promise<void> {
  await api.delete(`/api/chat/sessions/${id}`);
}
