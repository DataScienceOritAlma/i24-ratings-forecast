const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  metadata: Record<string, unknown>;
}

export async function predict(req: PredictRequest): Promise<PredictResponse> {
  const res = await fetch(`${API}/predict`, {
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
    headers: { "Content-Type": "application/json" },
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
