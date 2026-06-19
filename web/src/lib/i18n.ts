// Client-side i18n for the UI chrome (EN/ES).
//
// This translates only the *static UI chrome* — topbar, upload form, the
// in-place analyzing steps, and the report's section titles / chips / buttons.
//
// NOTE: the report's API-generated *content* (verdict text, summary, market
// rationales, recommendation text, citation source/detail) stays in English —
// it comes from the backend. Localizing report content will come from the LLM
// later by passing a `lang` param to the analysis request; the UI chrome here
// is the only thing translated client-side.

export type Lang = "en" | "es";

const STORAGE_KEY = "mm:lang";

export const messages: Record<Lang, Record<string, string>> = {
  en: {
    "foot": "MarketMind AI — commercial intelligence MVP",
    "nav.analyze": "Analyze",
    "nav.batch": "Batch · CSV",
    "nav.history": "History",
    "topbar.live": "LIVE · BACKEND",
    "idx.eyebrow": "New analysis",
    "idx.h1": "Analyze a <em>product</em>",
    "idx.sub":
      "Drop a few product photos and describe it in your own words. MarketMind reviews it against global demand, growth and marketplace signals — and writes you an explainable opportunity report.",
    "idx.images": "Product images",
    "idx.added": "added",
    "idx.description": "Description",
    "idx.freetext": "free text",
    "idx.drop": "Drag photos here, or click to add",
    "idx.dropsmall": "JPG / PNG · up to 8 images · resized client-side",
    "idx.hint": "Vision model infers <b>category &amp; attributes</b> — no forms to fill.",
    "idx.btn": "Analyze product",
    "idx.placeholder": "Describe your product in a sentence or two…",
    "idx.err.desc": "add a description first",
    "idx.err.failed": "request failed",
    "an.eyebrow": "Live analysis",
    "an.meta": "running the pipeline · streaming",
    "an.title": "Analyzing your product…",
    "an.step1": "Reading product images (vision)",
    "an.step2": "Classifying product & attributes",
    "an.step3": "Google Trends — demand trajectory",
    "an.step4": "World Bank + IMF — growth & geography",
    "an.step5": "eBay marketplace — live demand signal",
    "an.step6": "Scoring Market Opportunity (MOS)",
    "an.step7": "Writing explainable report",
    "res.attrs": "7 attributes",
    "res.classified": "classified",
    "res.trend": "+24% / 12 mo",
    "res.markets": "5 markets",
    "res.live": "live signal",
    "res.scored": "MOS scored",
    "res.ready": "ready",
    "rep.loading": "Loading report…",
    "rep.verdict": "Verdict",
    "rep.why": "Why — Market Opportunity Score breakdown",
    "rep.where": "Where — recommended markets",
    "rep.howmuch": "How much & when",
    "rep.recs": "Recommendations",
    "rep.sources": "Sources — every claim is cited",
    "rep.priceband": "Suggested price band",
    "rep.window": "Best launch window",
    "rep.copy": "Copy share link",
    "rep.new": "New analysis",
    "rep.pdf": "Download PDF",
    "rep.analyzed": "analyzed",
    "rep.image": "image",
    "rep.images": "images",
    "rep.sources_n": "sources",
    "rep.share": "share",
    "rep.copied": "Link copied",
    "tier.strong": "Strong opportunity",
    "tier.moderate": "Moderate opportunity",
    "tier.weak": "Watch · weak",
    "price.premium": "premium tier",
    "price.mid": "mid-market",
    "price.value": "value tier",
  },
  es: {
    "foot": "MarketMind AI — MVP de inteligencia comercial",
    "nav.analyze": "Analizar",
    "nav.batch": "Lote · CSV",
    "nav.history": "Historial",
    "topbar.live": "EN VIVO · BACKEND",
    "idx.eyebrow": "Nuevo análisis",
    "idx.h1": "Analiza un <em>producto</em>",
    "idx.sub":
      "Sube algunas fotos del producto y descríbelo con tus palabras. MarketMind lo analiza frente a señales globales de demanda, crecimiento y mercado — y te redacta un informe de oportunidad explicable.",
    "idx.images": "Imágenes del producto",
    "idx.added": "añadidas",
    "idx.description": "Descripción",
    "idx.freetext": "texto libre",
    "idx.drop": "Arrastra fotos aquí o haz clic para añadir",
    "idx.dropsmall": "JPG / PNG · hasta 8 imágenes · redimensionadas en el cliente",
    "idx.hint": "El modelo de visión infiere <b>categoría y atributos</b> — sin formularios.",
    "idx.btn": "Analizar producto",
    "idx.placeholder": "Describe tu producto en una o dos frases…",
    "idx.err.desc": "añade una descripción primero",
    "idx.err.failed": "error en la solicitud",
    "an.eyebrow": "Análisis en vivo",
    "an.meta": "ejecutando el pipeline · streaming",
    "an.title": "Analizando tu producto…",
    "an.step1": "Leyendo imágenes del producto (visión)",
    "an.step2": "Clasificando producto y atributos",
    "an.step3": "Google Trends — trayectoria de demanda",
    "an.step4": "Banco Mundial + FMI — crecimiento y geografía",
    "an.step5": "Marketplace eBay — señal de demanda en vivo",
    "an.step6": "Calculando el Market Opportunity (MOS)",
    "an.step7": "Redactando el informe explicable",
    "res.attrs": "7 atributos",
    "res.classified": "clasificado",
    "res.trend": "+24% / 12 m",
    "res.markets": "5 mercados",
    "res.live": "señal en vivo",
    "res.scored": "MOS calculado",
    "res.ready": "listo",
    "rep.loading": "Cargando informe…",
    "rep.verdict": "Veredicto",
    "rep.why": "Por qué — desglose del Market Opportunity Score",
    "rep.where": "Dónde — mercados recomendados",
    "rep.howmuch": "Cuánto y cuándo",
    "rep.recs": "Recomendaciones",
    "rep.sources": "Fuentes — cada afirmación está citada",
    "rep.priceband": "Banda de precio sugerida",
    "rep.window": "Mejor ventana de lanzamiento",
    "rep.copy": "Copiar enlace",
    "rep.new": "Nuevo análisis",
    "rep.pdf": "Descargar PDF",
    "rep.analyzed": "analizado",
    "rep.image": "imagen",
    "rep.images": "imágenes",
    "rep.sources_n": "fuentes",
    "rep.share": "compartir",
    "rep.copied": "Enlace copiado",
    "tier.strong": "Oportunidad fuerte",
    "tier.moderate": "Oportunidad moderada",
    "tier.weak": "Vigilar · débil",
    "price.premium": "gama premium",
    "price.mid": "mercado medio",
    "price.value": "gama económica",
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
