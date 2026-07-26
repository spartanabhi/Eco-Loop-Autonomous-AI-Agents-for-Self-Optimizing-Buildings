/**
 * Eco-Loop Building Agents API Utility
 * Connects to FastAPI Backend on http://127.0.0.1:8000
 */

const API_BASE = "http://127.0.0.1:8000";

export async function fetchHealth() {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error("Backend offline");
  return res.json();
}

export async function fetchStatus() {
  const res = await fetch(`${API_BASE}/api/status`);
  if (!res.ok) throw new Error("Status unavailable");
  return res.json();
}

export async function fetchHero() {
  const res = await fetch(`${API_BASE}/api/evaluation/hero`);
  if (!res.ok) throw new Error("Hero evaluation unavailable");
  return res.json();
}

export async function fetchLatestTelemetry() {
  const res = await fetch(`${API_BASE}/api/telemetry/latest`);
  if (!res.ok) throw new Error("Telemetry unavailable");
  return res.json();
}

export async function fetchTelemetryHistory(limit = 100) {
  const res = await fetch(`${API_BASE}/api/telemetry/history?limit=${limit}`);
  if (!res.ok) throw new Error("Telemetry history unavailable");
  return res.json();
}

export async function fetchLatestAgent() {
  const res = await fetch(`${API_BASE}/api/agent/latest`);
  if (!res.ok) throw new Error("Agent decision unavailable");
  return res.json();
}

export async function fetchAgentHistory(limit = 8) {
  const res = await fetch(`${API_BASE}/api/agent/history?limit=${limit}`);
  if (!res.ok) throw new Error("Agent history unavailable");
  return res.json();
}

export async function fetchActionHistory(limit = 8) {
  const res = await fetch(`${API_BASE}/api/actions?limit=${limit}`);
  if (!res.ok) throw new Error("Action history unavailable");
  return res.json();
}

export async function fetchEvaluationSummary() {
  const res = await fetch(`${API_BASE}/api/evaluation`);
  if (!res.ok) throw new Error("Evaluation summary unavailable");
  return res.json();
}

export async function fetchSeasons() {
  const res = await fetch(`${API_BASE}/api/seasons`);
  if (!res.ok) throw new Error("Seasons unavailable");
  return res.json();
}
