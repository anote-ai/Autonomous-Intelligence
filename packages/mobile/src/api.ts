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

// ---------------------------------------------------------------------------
// Autonomous run monitoring
// ---------------------------------------------------------------------------

export type RunStatus = "running" | "paused" | "awaiting_approval" | "failed" | "completed";

export interface Run {
  id: string;
  workflow: string;
  status: RunStatus;
  created_at: string;
  updated_at: string;
  steps_total: number;
  steps_done: number;
  artifact_count: number;
  error?: string;
}

export interface RunStep {
  id: string;
  name: string;
  status: "pending" | "running" | "done" | "failed";
  output?: string;
  started_at?: string;
  finished_at?: string;
  latency_ms?: number;
}

export interface Artifact {
  id: string;
  name: string;
  type: "text" | "json" | "image" | "file";
  preview?: string;
  size_bytes?: number;
  url?: string;
}

export interface ApprovalRequest {
  id: string;
  run_id: string;
  workflow: string;
  message: string;
  context?: string;
  created_at: string;
}

export interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  timestamp: string;
  detail?: string;
}

export interface RunDetail extends Run {
  steps: RunStep[];
  artifacts: Artifact[];
  approval?: ApprovalRequest;
  audit_log: AuditEntry[];
}

export async function getRuns(): Promise<Run[]> {
  const res = await api.get("/api/runs");
  return res.data.runs ?? [];
}

export async function getRunDetail(id: string): Promise<RunDetail> {
  const res = await api.get(`/api/runs/${id}`);
  return res.data;
}

export async function getPendingApprovals(): Promise<ApprovalRequest[]> {
  const res = await api.get("/api/runs/approvals");
  return res.data.approvals ?? [];
}

export async function approveRun(runId: string, approvalId: string, note?: string): Promise<void> {
  await api.post(`/api/runs/${runId}/approve`, { approval_id: approvalId, note });
}

export async function rejectRun(runId: string, approvalId: string, reason: string): Promise<void> {
  await api.post(`/api/runs/${runId}/reject`, { approval_id: approvalId, reason });
}

export async function pauseRun(runId: string): Promise<void> {
  await api.post(`/api/runs/${runId}/pause`);
}

export async function resumeRun(runId: string): Promise<void> {
  await api.post(`/api/runs/${runId}/resume`);
}

export async function retryRun(runId: string): Promise<void> {
  await api.post(`/api/runs/${runId}/retry`);
}
