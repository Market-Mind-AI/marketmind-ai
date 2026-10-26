// Renders a country's deterministic scores GROUPED by dimension, as aligned
// progress bars (same visual language as the MOS bar): one bar for the
// dimension subscore, and nested under it a bar for every signal that rolls up
// into it (e.g. Demand Quality → Growth, Demand Stability, Search Intent). Used
// inside each report country card (behind an expand toggle) and in the modal.
//
// Returns an animate() that grows every bar from 0 — call it when the content
// becomes visible (on expand / on modal open) so the animation actually plays.

import { formatNumber, type CountryEvidence, type ContextSignal, type DimensionEvidence, type SignalEvidence } from "./api";
import { t } from "./i18n";

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
  lang: string;
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
    `<span class="gs-val">${formatNumber(o.score, o.lang)}<small>/100</small></span></div>` +
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

/** One context indicator: its raw value and note, no bar (it has no score). */
function contextRow(c: ContextSignal, lang: string): HTMLElement {
  const node = document.createElement("div");
  node.className = "gs-bar sig";
  node.innerHTML =
    `<div class="gs-barhead"><span class="gs-lbl">${esc(c.label)}</span>` +
    `<span class="gs-val">${formatNumber(c.value, lang)}</span></div>` +
    (c.context ? `<div class="gs-ctx">${esc(c.context)}</div>` : "");
  return node;
}

/**
 * Build the grouped bars for a country into `container`. Dimensions come
 * pre-sorted by weight (highest first) from the Core. Returns animate().
 */
export function renderGroupedScores(container: HTMLElement, country: CountryEvidence, lang: string): () => void {
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
      lang,
      kind: "dim",
      meta:
        dim.weight != null
          ? `${dim.band_label} · ${t("rep.weight")} ${dim.weight.toLocaleString(lang, { style: "percent", maximumFractionDigits: 20 })}`
          : dim.band_label,
      explanation: dim.explanation,
    });
    group.appendChild(head.node);
    animations.push(head.animate);

    const kids = signals.filter((s) => s.dimension === dim.dimension);
    if (kids.length) {
      const children = document.createElement("div");
      children.className = "gs-children";
      for (const s of kids) {
        const b = bar({
          label: s.label,
          score: s.score,
          lang,
          kind: "sig",
          meta: s.band_label,
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

  // Context indicators (category volume, regional demand, government
  // expenditure) — a number with no score, shown but not part of the MOS.
  const ctx: ContextSignal[] = country.context_signals ?? [];
  if (ctx.length) {
    const group = document.createElement("div");
    group.className = "gs-group gs-context";
    const title = document.createElement("div");
    title.className = "gs-ctxtitle";
    title.textContent = t("rep.contextOnly");
    group.appendChild(title);
    const children = document.createElement("div");
    children.className = "gs-children";
    for (const c of ctx) children.appendChild(contextRow(c, lang));
    group.appendChild(children);
    container.appendChild(group);
  }

  return () => animations.forEach((a) => a());
}
