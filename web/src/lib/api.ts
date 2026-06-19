// Typed client for the MarketMind AI FastAPI backend.
// Base URL comes from the PUBLIC_API_BASE env var (exposed to the browser
// via Astro's PUBLIC_ convention). Falls back to localhost:8000.

export const API_BASE: string =
  (import.meta.env.PUBLIC_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8000";

/* ---------- response shapes (mirror infrastructure/api/schemas.py) ----------
   Verified against the live API in fake mode. Key facts:
   - POST /analyses returns { analysis_id, slug, status }  (NOT `id`)
   - GET /analyses/{id} returns `category` at the TOP LEVEL
   - score.contributions is an array of { factor, weight, normalized_score,
     contribution, imputed }  (NOT score.factors)
   - report fields are FLAT: price_low / price_high / currency / price_note /
     launch_label / launch_peak_note  (NOT nested price_band / launch_window)
   - SSE stream is GET /analyses/{id}/stream  (NOT /events)
-------------------------------------------------------------------------- */

export interface FactorContributionResponse {
  factor: string;
  weight: number;
  normalized_score: number;
  contribution: number;
  imputed: boolean;
}

export interface ScoreResponse {
  total: number;
  tier: string;
  explanation: string;
  contributions: FactorContributionResponse[];
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
  price_low: string;
  price_high: string;
  currency: string;
  price_note: string;
  launch_label: string;
  launch_peak_note: string;
  recommendations: string[];
  citations: CitationResponse[];
}

export interface AnalysisResponse {
  id: string;
  status: string;
  created_at: string;
  description: string;
  image_refs: string[];
  category: string | null;
  score: ScoreResponse | null;
  report: ReportResponse | null;
  failure_reason: string | null;
}

export interface AnalyzeResponse {
  analysis_id: string;
  slug: string;
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

/** SSE URL for GET /analyses/{id}/stream — open with `new EventSource(url)`. */
export function eventsUrl(id: string): string {
  return `${API_BASE}/analyses/${encodeURIComponent(id)}/stream`;
}

/**
 * Subscribe to the live progress stream. Returns a disposer that closes the
 * EventSource. Kept as a future enhancement — in fake mode the pipeline runs
 * synchronously inside the POST, so the analyzing page relies on GET polling,
 * not this stream.
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
  const s = status.toLowerCase();
  return s === "completed" || s === "failed";
}

/* ---------- helpers ---------- */

/** The share slug is the analysis UUID hex (dashes stripped). */
export function slugForId(id: string): string {
  return id.replace(/-/g, "").toLowerCase();
}

/** Reconstruct a UUID from a 32-char hex slug (insert dashes). */
export function idFromSlug(slug: string): string {
  const hex = slug.replace(/-/g, "").toLowerCase();
  if (hex.length !== 32) return slug; // already a uuid or unexpected — pass through
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/** Tier metadata for the UI (colors mirror the prototype).
 *  `key` is a stable identifier ("strong"|"moderate"|"weak") so callers can
 *  resolve a localized label via i18n: t("tier." + meta.key). `label` is the
 *  English fallback and is kept for non-localized contexts. */
export interface TierMeta {
  key: "strong" | "moderate" | "weak";
  label: string;
  color: string;
  border: string;
  bg: string;
}

export function tierMeta(tier: string): TierMeta {
  const t = tier.toLowerCase();
  if (t === "strong") {
    return {
      key: "strong",
      label: "Strong opportunity",
      color: "#5fd0ad",
      border: "rgba(95,208,173,.35)",
      bg: "rgba(95,208,173,.06)",
    };
  }
  if (t === "moderate") {
    return {
      key: "moderate",
      label: "Moderate opportunity",
      color: "#ecbc4e",
      border: "rgba(236,188,78,.35)",
      bg: "rgba(236,188,78,.06)",
    };
  }
  return {
    key: "weak",
    label: "Watch · weak",
    color: "#e96a4c",
    border: "rgba(233,106,76,.35)",
    bg: "rgba(233,106,76,.08)",
  };
}
