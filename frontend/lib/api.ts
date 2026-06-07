import { supabase } from "@/lib/supabase";

// Backend URL — HARDCODED (שלב 88, 2026-06-07). After 3 rounds of trying to
// resolve via NEXT_PUBLIC_API_URL + auto-detect, Vercel kept serving the env-var
// value (localhost:8000) and the browser threw "Failed to fetch" on every call.
// Decision: stop trying to be clever. The Render URL is public anyway. If we
// ever need local-dev to hit a local backend, the developer should comment this
// line out and use the env var. Production stays bulletproof.
const API = "https://i24-ratings-api.onrender.com";

// Build headers with the current Supabase access token attached so the
// backend's require_user() dependency can verify the caller.
async function authHeaders(): Promise<Record<string, string>> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

export interface PredictRequest {
  program_name: string;
  target_date: string;          // YYYY-MM-DD
  start_time: string;           // HH:MM:SS
  end_time?: string;
  scenario?: "routine" | "special_event";
  status?: string;
}

export interface PredictResponse {
  predicted_rating: number;            // adjusted rating (panel-corrected)
  prediction_low: number;              // 80% CI lower bound (adjusted)
  prediction_high: number;             // 80% CI upper bound (adjusted)
  predicted_rating_raw?: number;       // derived raw rating estimate
  reception_pct_used?: number;         // estimated panel reception
  estimated_households: number;
  estimated_viewers: number;
  model: string;
  target_kind?: string;                // "adjusted" | "raw"
  confidence_pct: number;
  uncertainty_source: string;
  // Cold-start signals (DEEP_ANALYSIS §C). Default to safe values for older backends.
  cold_start?: boolean;
  n_historical_broadcasts?: number;
  reliability?: "high" | "medium" | "cold_start";
  metadata: Record<string, unknown>;
  explanation?: string | null;         // LLM natural-language explanation (if enabled)
}

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${API}/predict`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export async function health(): Promise<{ status: string; model: string; history_rows: number }> {
  const res = await fetch(`${API}/health`);
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

export interface AskRequest { question: string; }

export interface AskResponse {
  question: string;
  answer: string;
  extracted: { program_name: string | null; target_date: string; scenario: string };
  prediction: PredictResponse | null;
  confidence: "high" | "medium" | "low";
}

export async function ask(req: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${API}/ask`, {
    method: "POST",
    headers: await authHeaders(),
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}

export interface CheckoutRequest {
  user_id: string;
  organization_id: string;
  email: string;
  return_url: string;
}

export interface CheckoutResponse {
  checkout_url: string;
  session_id: string;
}

export async function createCheckoutSession(req: CheckoutRequest): Promise<CheckoutResponse> {
  const res = await fetch(`${API}/checkout/create-session`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json();
}
