// Typed client for the MarketMind **Core** API (the marketmind-core service).
// Base URL comes from PUBLIC_API_BASE (exposed to the browser via Astro's
// PUBLIC_ convention). Falls back to the Core's default host port, 8004.
//
// The Core splits the flow into two calls on purpose:
//   1. POST /catalog/identify-image  — vision + enrichment, returns editable
//      fields (product, per-country search vocabulary, reference candidates).
//   2. POST /analyze                 — the user-confirmed fields + countries,
//      returns a request_id (202); poll GET /analyze/{request_id}.
// The MOS is computed per country by the backend; the browser never scores.

export const API_BASE: string =
  (import.meta.env.PUBLIC_API_BASE as string | undefined)?.replace(/\/$/, "") ??
  "http://localhost:8004";

/* ============================ shared shapes ============================ */

/** One country's curated search vocabulary (mirrors app/schemas/catalog.py
 *  LocalizedMarket). Keyed by ISO3 in `localized_markets`, so the country code
 *  lives in the map key, not here. */
export interface LocalizedMarket {
  primary_name: string;
  formal_name?: string | null;
  search_terms: string[];
  excluded_terms: string[];
  confidence: number;
}

/** One candidate biggest-market (mirrors ReferenceMarket). Carries its own
 *  ISO3 `country`. The largest by real search volume becomes the Demand Volume
 *  ruler ceiling; never scored itself. */
export interface ReferenceMarket extends LocalizedMarket {
  country: string;
}

/* ========================= identify-image ============================= */

export interface IdentifyImageResult {
  entity_key: string;
  canonical_title: string;
  method: string; // "alias" | "trigram" | "embedding" | "created"
  product_name: string;
  brand: string | null;
  category: string | null;
  localized_markets: Record<string, LocalizedMarket> | null;
  reference_candidates: ReferenceMarket[] | null;
  target_age_min: number | null;
  target_age_max: number | null;
  estimated_price: number | null;
  price_currency: string | null;
  confidence: number;
}

export type ImageMediaType =
  | "image/jpeg"
  | "image/png"
  | "image/gif"
  | "image/webp";

/** POST /catalog/identify-image — synchronous vision + enrichment call. */
export async function identifyImage(params: {
  // Image is optional — the product can be identified from the photo OR from the
  // text description (hintText). At least one must be provided.
  imageBase64?: string | null;
  mediaType?: ImageMediaType | null;
  hintText?: string;
  countries: string[];
}): Promise<IdentifyImageResult> {
  const res = await fetch(`${API_BASE}/catalog/identify-image`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      image_base64: params.imageBase64 ?? null,
      image_media_type: params.imageBase64 ? (params.mediaType ?? null) : null,
      hint_text: params.hintText ?? null,
      countries: params.countries,
    }),
  });
  if (!res.ok) {
    throw new Error(await errorDetail(res, "Failed to identify product"));
  }
  return (await res.json()) as IdentifyImageResult;
}

/* ============================== analyze =============================== */

/** Body of POST /analyze — the identify-image fields (user-confirmed) plus the
 *  target countries and optional price context. Field names mirror the Core's
 *  AnalyzeRequest exactly (pass-through from identify-image). */
export interface AnalyzeRequestBody {
  product_name: string;
  brand?: string | null;
  category?: string | null;
  localized_markets?: Record<string, LocalizedMarket> | null;
  reference_candidates?: ReferenceMarket[] | null;
  target_age_min?: number | null;
  target_age_max?: number | null;
  estimated_price?: number | null;
  price_currency?: string | null;
  user_prompt?: string | null;
  countries: string[];
}

export interface AnalyzeAcceptedResponse {
  request_id: string;
  status: string; // "pending"
}

/** POST /analyze — 202 Accepted, background pipeline. Poll getAnalysis(). */
export async function analyze(
  body: AnalyzeRequestBody,
): Promise<AnalyzeAcceptedResponse> {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(await errorDetail(res, "Failed to start analysis"));
  }
  return (await res.json()) as AnalyzeAcceptedResponse;
}

/* ============================ poll result ============================= */

/** One country's MOS result (mirrors app/schemas/mos.py MosResultResponse).
 *  Numeric fields arrive as JSON — Decimals serialize to strings, so they are
 *  typed `string | number | null` and normalized with `num()` before use. */
export interface MosResult {
  id: string;
  entity_key: string;
  country: string; // ISO3
  period_type: string;
  period_key: string;
  mos: string | number | null;
  mos_before_cap: string | number | null;
  capped_by: string | null;
  topsis_score: string | number | null;
  library_topsis_score: string | number | null;
  library_mos: string | number | null;
  mos_interpretation: string | null;
  explanation: string | null; // per-country note (may be null)
  availability_status: string;
  excluded_reason: string | null;
  computed_at: string;
  requested?: boolean; // false = off-request reference "champion" (best market for the product)
  is_champion?: boolean; // the highest-MOS market (crowned 👑)
}

/* ---------- rich evidence packet (breakdown) — mirrors the Core packet ---------- */

/** One dimension's subscore in the MOS aggregation. */
export interface DimensionEvidence {
  dimension: string;
  label: string;
  score: number;
  band: string;
  weight: number | null; // Rank-Reciprocal weight
  explanation: string;
}

/** One deterministic signal/metric under a dimension. */
export interface SignalEvidence {
  code: string;
  label: string;
  score: number;
  band: string;
  explanation: string;
  context?: string | null; // demand-volume carries absolute searches / population / penetration
  dimension?: string | null; // deterministic dimension this signal rolls up into ("context" = not scored)
}

export interface CountryEvidence {
  country: string; // ISO3
  mos: number | null;
  mos_band: string | null;
  mos_explanation: string | null;
  dimensions: DimensionEvidence[];
  signals: SignalEvidence[];
  demand_confidence?: string | null; // "low" = demand likely undercounted (missing native term)
  demand_confidence_note?: string | null;
  requested?: boolean; // false = off-request reference "champion"
  is_champion?: boolean; // the highest-MOS market (crowned 👑)
}

export interface DemandRuler {
  mode: string; // "reference" | "fixed"
  country?: string;
  volume?: number;
  candidates?: { country: string; volume: number }[];
}

export interface EvidencePacket {
  period_key: string;
  demand_ruler: DemandRuler | null;
  glossary: Record<string, { label: string; meaning: string }>;
  weights: Record<string, number>;
  countries: CountryEvidence[];
}

export interface AnalysisStatusResponse {
  request_id: string;
  status: string; // "pending" | "running" | "done" | "failed"
  canonical_title: string | null;
  user_prompt: string | null;
  result: MosResult[] | null;
  explanation: string | null; // LLM narrative of the whole ranking
  breakdown: EvidencePacket | null; // full per-country scores/metrics/explanations
  error_message: string | null;
}

/** GET /analyze/{request_id}. `result`/`explanation` populate once done. */
export async function getAnalysis(
  requestId: string,
): Promise<AnalysisStatusResponse> {
  const res = await fetch(
    `${API_BASE}/analyze/${encodeURIComponent(requestId)}`,
  );
  if (res.status === 404) {
    throw new Error("Analysis not found");
  }
  if (!res.ok) {
    throw new Error(await errorDetail(res, "Failed to load analysis"));
  }
  return (await res.json()) as AnalysisStatusResponse;
}

export function isTerminalStatus(status: string): boolean {
  const s = status.toLowerCase();
  return s === "done" || s === "failed";
}

/* ============================== helpers =============================== */

/** Coerce a Core numeric (Decimal-as-string | number | null) to a number. */
export function num(v: string | number | null | undefined): number | null {
  if (v === null || v === undefined) return null;
  const n = typeof v === "number" ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Read a File as a bare base64 string (no data: prefix) + its media type,
 *  the shape POST /catalog/identify-image expects. */
export function fileToImagePayload(
  file: File,
): Promise<{ base64: string; mediaType: ImageMediaType }> {
  const allowed: ImageMediaType[] = [
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
  ];
  const mediaType = (
    allowed.includes(file.type as ImageMediaType) ? file.type : "image/jpeg"
  ) as ImageMediaType;
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Could not read the image file"));
    reader.onload = () => {
      const result = String(reader.result);
      const comma = result.indexOf(",");
      resolve({
        base64: comma >= 0 ? result.slice(comma + 1) : result,
        mediaType,
      });
    };
    reader.readAsDataURL(file);
  });
}

async function errorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    const detail = (data as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (detail) return JSON.stringify(detail);
  } catch {
    /* body was not JSON */
  }
  return `${fallback} (${res.status})`;
}

/* ---------- country catalog (fetched from the Core: GET /countries) ---------- */
// The available markets are served by the Core, ordered by continent then name
// (the markets Google Ads can measure — see marketmind-core
// docs/paises-disponiveis.md). Fetched once and cached; countryName()/flag()
// resolve from that cache, so a caller must ensure fetchCountries() has resolved
// before rendering names/flags (each page awaits it on init).

export interface CountryMeta {
  iso3: string;
  name: string;
  iso2: string | null;
  continent: string | null;
}

/** Default target-market basket prefilled in the picker. */
export const DEFAULT_COUNTRIES: string[] = ["BRA", "USA", "DEU", "JPN"];

let _countries: CountryMeta[] = [];
const _byIso3 = new Map<string, CountryMeta>();
let _countriesPromise: Promise<CountryMeta[]> | null = null;

/** GET /countries — available markets ordered by (continent, name). Cached;
 *  safe to call repeatedly (concurrent calls share one in-flight request). */
export async function fetchCountries(): Promise<CountryMeta[]> {
  if (_countries.length) return _countries;
  if (!_countriesPromise) {
    _countriesPromise = (async () => {
      const res = await fetch(`${API_BASE}/countries`);
      if (!res.ok) throw new Error(await errorDetail(res, "Failed to load countries"));
      const list = (await res.json()) as CountryMeta[];
      _countries = list;
      _byIso3.clear();
      for (const c of list) _byIso3.set(c.iso3.toUpperCase(), c);
      return list;
    })();
  }
  try {
    return await _countriesPromise;
  } catch (err) {
    _countriesPromise = null; // allow a retry on the next call
    throw err;
  }
}

/** The cached list (empty until fetchCountries() resolves). */
export function countries(): CountryMeta[] {
  return _countries;
}

export function countryMeta(iso3: string): CountryMeta | undefined {
  return _byIso3.get(iso3?.toUpperCase());
}

export function countryName(iso3: string): string {
  return countryMeta(iso3)?.name ?? iso3;
}

/** Flag emoji from an ISO2 (or ISO3, resolved via the cached catalog). */
export function flag(code: string): string {
  let iso2 = code?.toUpperCase() ?? "";
  if (iso2.length === 3) iso2 = countryMeta(iso2)?.iso2?.toUpperCase() ?? "";
  if (iso2.length !== 2) return "🏳️";
  return iso2.replace(/./g, (c) =>
    String.fromCodePoint(127397 + c.charCodeAt(0)),
  );
}

/* ---------- MOS tier (color + key) from the numeric score ---------- */
// The Core returns a textual `mos_interpretation` band; for the gauge/chip
// color we derive a coarse tier from the number. Thresholds are presentational
// only (they do not affect any score).

export interface TierMeta {
  key: "strong" | "moderate" | "weak";
  color: string;
  border: string;
  bg: string;
}

export function mosTier(mos: number | null): TierMeta {
  if (mos !== null && mos >= 60) {
    return {
      key: "strong",
      color: "#5fd0ad",
      border: "rgba(95,208,173,.35)",
      bg: "rgba(95,208,173,.06)",
    };
  }
  if (mos !== null && mos >= 40) {
    return {
      key: "moderate",
      color: "#ecbc4e",
      border: "rgba(236,188,78,.35)",
      bg: "rgba(236,188,78,.06)",
    };
  }
  return {
    key: "weak",
    color: "#e96a4c",
    border: "rgba(233,106,76,.35)",
    bg: "rgba(233,106,76,.08)",
  };
}

/** The share slug is the request UUID hex (dashes stripped). */
export function slugForId(id: string): string {
  return id.replace(/-/g, "").toLowerCase();
}

/** Reconstruct a UUID from a 32-char hex slug (insert dashes). */
export function idFromSlug(slug: string): string {
  const hex = slug.replace(/-/g, "").toLowerCase();
  if (hex.length !== 32) return slug;
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

/* ---------- live status stream (SSE) ---------- */

export interface StatusEvent {
  request_id: string;
  status: string; // pending | running | done | failed | not_found
  timeout?: boolean;
}

/**
 * Subscribe to GET /analyze/{id}/stream. Calls `onStatus` on each status event.
 * The Core closes the stream on a terminal state; we close the EventSource too
 * (so the browser does not auto-reconnect). Returns a disposer.
 */
export function subscribeStatus(
  id: string,
  onStatus: (status: string, event: StatusEvent) => void,
  onError?: (err: Event) => void,
): () => void {
  const source = new EventSource(`${API_BASE}/analyze/${encodeURIComponent(id)}/stream`);
  const close = () => source.close();
  source.onmessage = (msg: MessageEvent) => {
    try {
      const data = JSON.parse(msg.data) as StatusEvent;
      onStatus(data.status, data);
      if (isTerminalStatus(data.status) || data.status === "not_found") close();
    } catch {
      /* ignore malformed frame */
    }
  };
  source.onerror = (err) => onError?.(err);
  return close;
}

/* ---------- pending-requests store (localStorage) ---------- */
// Lets the pending-analyses dock survive navigation and reloads. Holds only
// lightweight metadata; the full result/breakdown is fetched on demand.

export interface StoredRequest {
  id: string;
  title: string;
  countries: string[];
  status: string; // pending | running | done | failed
  createdAt: number;
}

const REQ_KEY = "mm:requests";
const REQ_MAX = 40;

export function loadRequests(): StoredRequest[] {
  if (typeof localStorage === "undefined") return [];
  try {
    const raw = localStorage.getItem(REQ_KEY);
    const list = raw ? (JSON.parse(raw) as StoredRequest[]) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

function persistRequests(list: StoredRequest[]): void {
  if (typeof localStorage === "undefined") return;
  try {
    localStorage.setItem(REQ_KEY, JSON.stringify(list.slice(0, REQ_MAX)));
  } catch {
    /* storage full / unavailable */
  }
}

/** Upsert a request at the front of the list. Returns the new list. */
export function saveRequest(entry: StoredRequest): StoredRequest[] {
  const list = loadRequests().filter((r) => r.id !== entry.id);
  list.unshift(entry);
  persistRequests(list);
  return list;
}

/** Patch a stored request (e.g. status change). Returns the new list. */
export function patchRequest(id: string, patch: Partial<StoredRequest>): StoredRequest[] {
  const list = loadRequests().map((r) => (r.id === id ? { ...r, ...patch } : r));
  persistRequests(list);
  return list;
}

/** Remove a stored request. Returns the new list. */
export function removeRequest(id: string): StoredRequest[] {
  const list = loadRequests().filter((r) => r.id !== id);
  persistRequests(list);
  return list;
}
