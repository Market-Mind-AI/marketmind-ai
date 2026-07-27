// Client-side i18n for the UI chrome (EN/ES).
//
// This translates only the *static UI chrome* — topbar, upload form, the
// review screen, the analyzing steps, and the report's section titles / chips /
// buttons.
//
// NOTE: the report's backend-generated *content* — above all the MOS narrative
// (`explanation`) and each country's `mos_interpretation` — is rendered as-is.
// The Core produces the narrative in its own configured language (default PT),
// independent of this chrome language.

export type Lang = "en" | "es";

const STORAGE_KEY = "mm:lang";

export const messages: Record<Lang, Record<string, string>> = {
  en: {
    "foot": "MarketMind AI — commercial intelligence MVP",
    "nav.analyze": "Analyze",
    "nav.batch": "Batch · CSV",
    "nav.history": "History",
    "topbar.live": "LIVE · CORE",
    // --- upload ---
    "idx.eyebrow": "New analysis",
    "idx.h1": "Analyze a <em>product</em>",
    "idx.sub":
      "Add a product photo, describe it in your own words, and pick the target markets. MarketMind identifies the product, then scores each market against global demand, growth and geographic signals — with an explainable narrative.",
    "idx.images": "Product image",
    "idx.added": "added",
    "idx.description": "Description",
    "idx.freetext": "free text",
    "idx.drop": "Drag a photo here, or click to add",
    "idx.dropsmall": "JPG / PNG · the first image is used for identification",
    "idx.markets": "Target markets",
    "idx.markets.hint": "Pick the countries to score.",
    "idx.hint": "We'll identify your product from the photo — <b>you review it</b> next.",
    "idx.btn": "Identify product",
    "idx.identifying": "Identifying…",
    "idx.identifying.hint": "Reading the photo and preparing the markets — this can take a few seconds.",
    "idx.placeholder": "Describe your product in a sentence or two…",
    "idx.err.desc": "add a description first",
    "idx.err.img": "add a product image first",
    "idx.err.markets": "pick at least one market",
    "idx.err.failed": "request failed",
    // --- review ---
    "rev.eyebrow": "Review & confirm",
    "rev.title": "Confirm before analyzing",
    "rev.sub": "Confirm the product identity. Everything else is inferred automatically.",
    "rev.note": "The search vocabulary per market is generated automatically — you only confirm the product identity above.",
    "rev.identity": "Product identity",
    "rev.name": "Product name",
    "rev.brand": "Brand",
    "rev.category": "Category",
    "rev.price": "Est. price (context only)",
    "rev.currency": "Currency",
    "rev.agemin": "Target age — min",
    "rev.agemax": "Target age — max",
    "rev.markets": "Per-market search vocabulary",
    "rev.primary": "Primary name",
    "rev.terms": "Search terms",
    "rev.excluded": "Excluded terms",
    "rev.commas": "comma-separated",
    "rev.refs": "Reference-market candidates",
    "rev.refs.hint": "The largest by real search volume becomes the Demand Volume ruler. Context only — never scored.",
    "rev.conf": "confidence",
    "rev.none": "none",
    "rev.back": "Back",
    "rev.analyze": "Confirm & analyze",
    "rev.analyzing": "Analyzing…",
    "rev.submitting": "Sending for analysis…",
    // --- analyzing ---
    "an.eyebrow": "Live analysis",
    "an.meta": "running the pipeline",
    "an.title": "Analyzing your product…",
    "an.step1": "Ensuring data freshness (last 6 months)",
    "an.step2": "Collecting missing signals (Trends · World Bank · UN · OECD)",
    "an.step3": "Computing Cap. 4 indicators",
    "an.step4": "Computing the MOS per country (Cap. 5)",
    "an.step5": "Writing the business narrative",
    // --- report ---
    "rep.loading": "Loading report…",
    "rep.ranking": "Market Opportunity ranking",
    "rep.mos": "MOS / 100",
    "rep.narrative": "Analysis",
    "rep.cappedby": "capped by",
    "rep.lowconfidence": "demand may be undercounted",
    "rep.excluded": "excluded",
    "rep.na": "n/a",
    "rep.period": "period",
    "rep.analyzed": "analyzed",
    "rep.copy": "Copy share link",
    "rep.new": "New analysis",
    "rep.share": "share",
    "rep.copied": "Link copied",
    "rep.dimensions": "Dimensions — weighted subscores",
    "rep.signals": "Deterministic signals",
    "rep.comparison": "Comparison — MOS & all scores",
    "rep.metric": "Metric",
    "rep.youasked": "You asked",
    "tier.strong": "Strong opportunity",
    "tier.moderate": "Moderate opportunity",
    "tier.weak": "Watch · weak",
    // --- dock ---
    "dock.title": "Analyses",
    "dock.empty": "No analyses yet.",
    "dock.clear": "Clear finished",
    "dock.pending": "queued",
    "dock.running": "running",
    "dock.done": "ready",
    "dock.failed": "failed",
  },
  es: {
    "foot": "MarketMind AI — MVP de inteligencia comercial",
    "nav.analyze": "Analizar",
    "nav.batch": "Lote · CSV",
    "nav.history": "Historial",
    "topbar.live": "EN VIVO · CORE",
    // --- upload ---
    "idx.eyebrow": "Nuevo análisis",
    "idx.h1": "Analiza un <em>producto</em>",
    "idx.sub":
      "Añade una foto del producto, descríbelo con tus palabras y elige los mercados objetivo. MarketMind identifica el producto y luego puntúa cada mercado frente a señales globales de demanda, crecimiento y geografía — con una narrativa explicable.",
    "idx.images": "Imagen del producto",
    "idx.added": "añadidas",
    "idx.description": "Descripción",
    "idx.freetext": "texto libre",
    "idx.drop": "Arrastra una foto aquí o haz clic para añadir",
    "idx.dropsmall": "JPG / PNG · la primera imagen se usa para identificar",
    "idx.markets": "Mercados objetivo",
    "idx.markets.hint": "Elige los países a puntuar.",
    "idx.hint": "Identificaremos tu producto a partir de la foto — <b>tú lo revisas</b> a continuación.",
    "idx.btn": "Identificar producto",
    "idx.identifying": "Identificando…",
    "idx.identifying.hint": "Leyendo la foto y preparando los mercados — puede tardar unos segundos.",
    "idx.placeholder": "Describe tu producto en una o dos frases…",
    "idx.err.desc": "añade una descripción primero",
    "idx.err.img": "añade una imagen del producto primero",
    "idx.err.markets": "elige al menos un mercado",
    "idx.err.failed": "error en la solicitud",
    // --- review ---
    "rev.eyebrow": "Revisar y confirmar",
    "rev.title": "Confirma antes de analizar",
    "rev.sub": "Confirma la identidad del producto. Todo lo demás se infiere automáticamente.",
    "rev.note": "El vocabulario de búsqueda por mercado se genera automáticamente — solo confirmas la identidad del producto arriba.",
    "rev.identity": "Identidad del producto",
    "rev.name": "Nombre del producto",
    "rev.brand": "Marca",
    "rev.category": "Categoría",
    "rev.price": "Precio est. (solo contexto)",
    "rev.currency": "Moneda",
    "rev.agemin": "Edad objetivo — mín",
    "rev.agemax": "Edad objetivo — máx",
    "rev.markets": "Vocabulario de búsqueda por mercado",
    "rev.primary": "Nombre principal",
    "rev.terms": "Términos de búsqueda",
    "rev.excluded": "Términos excluidos",
    "rev.commas": "separados por comas",
    "rev.refs": "Candidatos de mercado de referencia",
    "rev.refs.hint": "El mayor por volumen real de búsquedas se vuelve la regla de Demand Volume. Solo contexto — nunca puntuado.",
    "rev.conf": "confianza",
    "rev.none": "ninguno",
    "rev.back": "Volver",
    "rev.analyze": "Confirmar y analizar",
    "rev.analyzing": "Analizando…",
    "rev.submitting": "Enviando para análisis…",
    // --- analyzing ---
    "an.eyebrow": "Análisis en vivo",
    "an.meta": "ejecutando el pipeline",
    "an.title": "Analizando tu producto…",
    "an.step1": "Asegurando frescura de datos (últimos 6 meses)",
    "an.step2": "Recolectando señales faltantes (Trends · Banco Mundial · ONU · OCDE)",
    "an.step3": "Calculando indicadores del Cap. 4",
    "an.step4": "Calculando el MOS por país (Cap. 5)",
    "an.step5": "Redactando la narrativa de negocio",
    // --- report ---
    "rep.loading": "Cargando informe…",
    "rep.ranking": "Ranking de Market Opportunity",
    "rep.mos": "MOS / 100",
    "rep.narrative": "Análisis",
    "rep.cappedby": "limitado por",
    "rep.lowconfidence": "demanda pode estar subestimada",
    "rep.excluded": "excluido",
    "rep.na": "n/d",
    "rep.period": "periodo",
    "rep.analyzed": "analizado",
    "rep.copy": "Copiar enlace",
    "rep.new": "Nuevo análisis",
    "rep.share": "compartir",
    "rep.copied": "Enlace copiado",
    "rep.dimensions": "Dimensiones — subpuntajes ponderados",
    "rep.signals": "Señales deterministas",
    "rep.comparison": "Comparativa — MOS y todos los scores",
    "rep.metric": "Métrica",
    "rep.youasked": "Preguntaste",
    "tier.strong": "Oportunidad fuerte",
    "tier.moderate": "Oportunidad moderada",
    "tier.weak": "Vigilar · débil",
    // --- dock ---
    "dock.title": "Análisis",
    "dock.empty": "Aún no hay análisis.",
    "dock.clear": "Limpiar finalizados",
    "dock.pending": "en cola",
    "dock.running": "procesando",
    "dock.done": "listo",
    "dock.failed": "falló",
  },
};

/** Read the active language: localStorage override → navigator default → "en". */
export function getLang(): Lang {
  if (typeof localStorage === "undefined") return "en";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "es") return stored;
  if (typeof navigator !== "undefined" && navigator.language?.startsWith("es")) {
    return "es";
  }
  return "en";
}

/** Persist the chosen language. */
export function setLang(l: Lang): void {
  if (typeof localStorage === "undefined") return;
  localStorage.setItem(STORAGE_KEY, l);
}

/** Translate a key for the given (or active) language, with EN fallback. */
export function t(key: string, lang?: Lang): string {
  const l = lang ?? getLang();
  return messages[l][key] ?? messages.en[key] ?? key;
}

/**
 * Translate every `[data-i18n]` (textContent), `[data-i18n-html]` (innerHTML),
 * and `[data-i18n-ph]` (placeholder) element under `root` for the active lang,
 * and set `<html lang>`.
 */
export function applyTranslations(root: ParentNode = document): void {
  const lang = getLang();
  if (typeof document !== "undefined") {
    document.documentElement.lang = lang;
  }
  root.querySelectorAll<HTMLElement>("[data-i18n]").forEach((el) => {
    const key = el.getAttribute("data-i18n");
    if (key) el.textContent = t(key, lang);
  });
  root.querySelectorAll<HTMLElement>("[data-i18n-html]").forEach((el) => {
    const key = el.getAttribute("data-i18n-html");
    if (key) el.innerHTML = t(key, lang);
  });
  root.querySelectorAll<HTMLElement>("[data-i18n-ph]").forEach((el) => {
    const key = el.getAttribute("data-i18n-ph");
    if (key) (el as HTMLInputElement | HTMLTextAreaElement).placeholder = t(key, lang);
  });
}
