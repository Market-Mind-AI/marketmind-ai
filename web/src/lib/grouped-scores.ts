// Renders a country's deterministic scores GROUPED by dimension, as aligned
// progress bars (same visual language as the MOS bar): one bar for the
// dimension subscore, and nested under it a bar for every signal that rolls up
// into it (e.g. Demand Quality → Growth, Demand Stability, Search Intent). Used
// inside each report country card (behind an expand toggle) and in the modal.
//
// Returns an animate() that grows every bar from 0 — call it when the content
// becomes visible (on expand / on modal open) so the animation actually plays.

import type { CountryEvidence, DimensionEvidence, SignalEvidence } from "./api";

// Fallback dimension for a signal, for evidence packets stored before the Core
// tagged signals with their dimension. Mirrors DIMENSION_BY_INDICATOR.
const DIMENSION_BY_SIGNAL: Record<string, string> = {
  trend_score: "demand_volume",
  growth_score: "demand_quality",
  demand_stability_score: "demand_quality",
  search_intent_score: "demand_quality",
  internet_penetration_score: "digital_readiness",
  mobile_connectivity_score: "digital_readiness",
  broadband_adoption_score: "digital_readiness",
  gdp_per_capita_score: "economic_readiness",
  gdp_growth_score: "economic_readiness",
  worldbank_inflation_score: "economic_readiness",
  real_estate_growth_score: "economic_readiness",
  population_scale_score: "market_size",
  urbanization_score: "market_size",
  population_growth_score: "demographic_sustainability",
  net_migration_rate_score: "demographic_sustainability",
  median_age_fit_score: "demographic_sustainability",
  consumer_spending_score: "macro_demand_structure",
  investment_score: "macro_demand_structure",
  net_exports_score: "macro_demand_structure",
  trade_openness_score: "macro_demand_structure",
  regional_demand_score: "context",
  government_expenditure_score: "context",
};

function dimOf(s: SignalEvidence): string {
  return s.dimension || DIMENSION_BY_SIGNAL[s.code] || "context";
}

/** The deterministic dimension a signal rolls up into ("context" = not scored).
 *  Exported so the comparison table groups signals the same way. */
export function signalDimension(s: SignalEvidence): string {
  return dimOf(s);
}

let escEl: HTMLElement | null = null;
function esc(s: string): string {
  if (!escEl) escEl = document.createElement("div");
  escEl.textContent = s ?? "";
  return escEl.innerHTML;
}

const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

/** One aligned progress-bar row (dimension or signal). */
function bar(o: {
  label: string;
  score: number;
  kind: "dim" | "sig";
  meta?: string;
  explanation?: string;
  context?: string | null;
}): { node: HTMLElement; animate: () => void } {
  const node = document.createElement("div");
  node.className = `gs-bar ${o.kind}`;
  const w = Math.max(0, Math.min(100, o.score));
  node.innerHTML =
    `<div class="gs-barhead"><span class="gs-lbl">${esc(o.label)}</span>` +
    `<span class="gs-val">${Math.round(o.score)}<small>/100</small></span></div>` +
    `<div class="gs-track"><div class="gs-fill"></div></div>` +
    (o.meta ? `<div class="gs-meta">${esc(o.meta)}</div>` : "") +
    (o.explanation ? `<div class="gs-expl">${esc(o.explanation)}</div>` : "") +
    (o.context ? `<div class="gs-ctx">${esc(o.context)}</div>` : "");
  const fill = node.querySelector<HTMLElement>(".gs-fill")!;
  const animate = () => {
    if (reduceMotion()) {
      fill.style.width = `${w}%`;
      return;
    }
    fill.style.transition = "none";
    fill.style.width = "0%";
    requestAnimationFrame(() => {
      fill.style.transition = "width 1s cubic-bezier(.2,.75,.2,1)";
      fill.style.width = `${w}%`;
    });
  };
  return { node, animate };
}

/**
 * Build the grouped bars for a country into `container`. Dimensions come
 * pre-sorted by weight (highest first) from the Core. Returns animate().
 */
export function renderGroupedScores(container: HTMLElement, country: CountryEvidence): () => void {
  container.innerHTML = "";
  const animations: (() => void)[] = [];
  const dims: DimensionEvidence[] = country.dimensions ?? [];
  const signals: SignalEvidence[] = country.signals ?? [];

  for (const dim of dims) {
    const group = document.createElement("div");
    group.className = "gs-group";

    const head = bar({
      label: dim.label,
      score: dim.score,
      kind: "dim",
      meta: dim.weight != null ? `${dim.band} · peso ${Math.round(dim.weight * 100)}%` : dim.band,
      explanation: dim.explanation,
    });
    group.appendChild(head.node);
    animations.push(head.animate);

    const kids = signals.filter((s) => dimOf(s) === dim.dimension);
    if (kids.length) {
      const children = document.createElement("div");
      children.className = "gs-children";
      for (const s of kids) {
        const b = bar({
          label: s.label,
          score: s.score,
          kind: "sig",
          meta: s.band,
          explanation: s.explanation,
          context: s.context,
        });
        children.appendChild(b.node);
        animations.push(b.animate);
      }
      group.appendChild(children);
    }
    container.appendChild(group);
  }

  // Context-only signals (regional demand, government expenditure) — computed
  // and shown, but not scored into any dimension.
  const ctx = signals.filter((s) => dimOf(s) === "context");
  if (ctx.length) {
    const group = document.createElement("div");
    group.className = "gs-group gs-context";
    group.innerHTML = `<div class="gs-ctxtitle">Contexto — não pontuado no MOS</div>`;
    const children = document.createElement("div");
    children.className = "gs-children";
    for (const s of ctx) {
      const b = bar({
        label: s.label,
        score: s.score,
        kind: "sig",
        meta: s.band,
        explanation: s.explanation,
        context: s.context,
      });
      children.appendChild(b.node);
      animations.push(b.animate);
    }
    group.appendChild(children);
    container.appendChild(group);
  }

  return () => animations.forEach((a) => a());
}
