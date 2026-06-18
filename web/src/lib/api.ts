// Typed client for the MarketMind AI FastAPI backend.
// Base URL comes from the PUBLIC_API_BASE env var (exposed to the browser
// via Astro's PUBLIC_ convention). Falls back to localhost:8000.

export const API_BASE: string =
  (import.meta.env.PUBLIC_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

/* ---------- response shapes (mirror infrastructure/api/schemas.py) ---------- */

export interface FactorContributionResponse {
  factor: string;
  raw_value: number;
  normalized_score: number;
  weight: number;
  contribution: number;
  imputed: boolean;
}

export interface ScoreResponse {
  total: number;
  tier: string;
  explanation: string;
  factors: FactorContributionResponse[];
}

export interface MarketResponse {
  country_code: string;
  country_name: string;
  score: number;
  rationale: string;
}

export interface CitationResponse {
  source: string;
  detail: string;
  as_of: string;
}

export interface ReportResponse {
  verdict: string;
  summary: string;
  markets: MarketResponse[];
  price_band: {
    low: string;
    high: string;
    currency: string;
    note: string;
  };
  launch_window: { label: string; peak_note: string };
  recommendations: string[];
  citations: CitationResponse[];
}

export interface AnalysisResponse {
  id: string;
  status: string;
  description: string;
  image_refs: string[];
  attributes?: {
    category: string;
    subcategory: string;
    materials: string[];
    color: string;
    style: string;
    key_features: string[];
    suggested_keywords: string[];
    confidence: number;
  } | null;
  score?: ScoreResponse | null;
  report?: ReportResponse | null;
  failure_reason?: string | null;
}

export interface AnalyzeResponse {
  id: string;
  status: string;
}

export interface ProgressEvent {
  step: string;
  detail: string;
}

/* ---------- endpoints ---------- */

/** POST /analyses — multipart description + image files. */
export async function createAnalysis(
  description: string,
  images: File[],
): Promise<AnalyzeResponse> {
  const form = new FormData();
  form.append("description", description);
  for (const img of images) {
    form.append("images", img, img.name);
  }
  const res = await fetch(`${API_BASE}/analyses`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) {
    throw new Error(`Failed to create analysis (${res.status})`);
  }
  return (await res.json()) as AnalyzeResponse;
}

/** GET /analyses/{id} */
export async function getAnalysis(id: string): Promise<AnalysisResponse> {
  const res = await fetch(`${API_BASE}/analyses/${encodeURIComponent(id)}`);
  if (res.status === 404) {
    throw new Error("Analysis not found");
  }
  if (!res.ok) {
    throw new Error(`Failed to load analysis (${res.status})`);
  }
  return (await res.json()) as AnalysisResponse;
}

/** SSE URL for GET /analyses/{id}/events — open with `new EventSource(url)`. */
export function eventsUrl(id: string): string {
  return `${API_BASE}/analyses/${encodeURIComponent(id)}/events`;
}

/**
 * Subscribe to the live progress stream. Returns a disposer that closes the
 * EventSource. The backend publishes steps: extracting, enriching, scoring,
 * embedding, reporting, completed, failed.
 */
export function subscribeProgress(
  id: string,
  handlers: {
    onEvent: (event: ProgressEvent) => void;
    onError?: (err: Event) => void;
  },
): () => void {
  const source = new EventSource(eventsUrl(id));
  source.onmessage = (msg: MessageEvent) => {
    try {
      const data = JSON.parse(msg.data) as ProgressEvent;
      handlers.onEvent(data);
    } catch {
      handlers.onEvent({ step: "message", detail: String(msg.data) });
    }
  };
  source.onerror = (err) => {
    handlers.onError?.(err);
  };
  return () => source.close();
}

/** Downloadable PDF report URL. */
export function reportPdfUrl(id: string): string {
  return `${API_BASE}/analyses/${encodeURIComponent(id)}/report.pdf`;
}

export function isTerminalStatus(status: string): boolean {
  return status === "completed" || status === "failed" || status === "COMPLETED" || status === "FAILED";
}
