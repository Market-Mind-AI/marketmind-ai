// Rich MOS breakdown modal. Given an analysis request id, fetches the full
// evidence packet (breakdown) and renders it: a big animated MOS speedometer
// per country (the focus), animated bars for every dimension subscore and
// deterministic signal (each with its explanation), and the LLM narrative.
// Charts re-animate every time the modal opens or the country tab changes.
//
// All chart drawing is hand-rolled SVG/DOM — no external chart library — so it
// works under Astro's static output with zero extra dependencies.

import {
  getAnalysis,
  isTerminalStatus,
  num,
  flag,
  countryName,
  mosTier,
  type AnalysisStatusResponse,
  type CountryEvidence,
} from "./api";
import { t } from "./i18n";

let escEl: HTMLElement | null = null;

function esc(s: string): string {
  if (!escEl) escEl = document.createElement("div");
  escEl.textContent = s ?? "";
  return escEl.innerHTML;
}

function reduceMotion(): boolean {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Build a semicircular speedometer gauge. Returns the SVG element plus an
 *  animate() that sweeps the needle + arc and counts the number up. */
function speedometer(value: number | null, opts: { size?: number; big?: boolean } = {}) {
  const v = value === null ? 0 : Math.max(0, Math.min(100, value));
  const size = opts.size ?? 220;
  const color = mosTier(value).color;
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 200 128");
  svg.setAttribute("width", String(size));
  svg.setAttribute("class", "spdo" + (opts.big ? " big" : ""));

  const ARC = "M 18,108 A 90,90 0 0 1 182,108"; // ~180° arc, length ≈ 282.7
  const LEN = 282.7;

  const track = document.createElementNS(ns, "path");
  track.setAttribute("d", ARC);
  track.setAttribute("fill", "none");
  track.setAttribute("stroke", "rgba(255,255,255,.08)");
  track.setAttribute("stroke-width", "13");
  track.setAttribute("stroke-linecap", "round");
  svg.appendChild(track);

  const fill = document.createElementNS(ns, "path");
  fill.setAttribute("d", ARC);
  fill.setAttribute("fill", "none");
  fill.setAttribute("stroke", color);
  fill.setAttribute("stroke-width", "13");
  fill.setAttribute("stroke-linecap", "round");
  fill.setAttribute("stroke-dasharray", String(LEN));
  fill.setAttribute("stroke-dashoffset", String(LEN));
  svg.appendChild(fill);

  // needle
  const needle = document.createElementNS(ns, "line");
  needle.setAttribute("x1", "100");
  needle.setAttribute("y1", "108");
  needle.setAttribute("x2", "100");
  needle.setAttribute("y2", "38");
  needle.setAttribute("stroke", color);
  needle.setAttribute("stroke-width", "3.5");
  needle.setAttribute("stroke-linecap", "round");
  needle.style.transformOrigin = "100px 108px";
  needle.style.transform = "rotate(-90deg)";
  svg.appendChild(needle);

  const hub = document.createElementNS(ns, "circle");
  hub.setAttribute("cx", "100");
  hub.setAttribute("cy", "108");
  hub.setAttribute("r", "6");
  hub.setAttribute("fill", color);
  svg.appendChild(hub);

  const label = document.createElementNS(ns, "text");
  label.setAttribute("x", "100");
  label.setAttribute("y", "98");
  label.setAttribute("text-anchor", "middle");
  label.setAttribute("class", "spdo-num");
  label.textContent = "0";
  svg.appendChild(label);

  const animate = () => {
    const targetDeg = (v / 100) * 180 - 90;
    const targetOff = LEN * (1 - v / 100);
    if (reduceMotion()) {
      needle.style.transform = `rotate(${targetDeg}deg)`;
      fill.setAttribute("stroke-dashoffset", String(targetOff));
      label.textContent = value === null ? "—" : String(Math.round(v));
      return;
    }
    needle.style.transition = "transform 1.15s cubic-bezier(.2,.75,.2,1)";
    fill.style.transition = "stroke-dashoffset 1.15s cubic-bezier(.2,.75,.2,1)";
    requestAnimationFrame(() => {
      needle.style.transform = `rotate(${targetDeg}deg)`;
      fill.setAttribute("stroke-dashoffset", String(targetOff));
    });
    if (value === null) {
      label.textContent = "—";
      return;
    }
    let n = 0;
    const step = Math.max(1, Math.round(v / 42));
    const timer = setInterval(() => {
      n += step;
      if (n >= v) {
        n = Math.round(v);
        clearInterval(timer);
      }
      label.textContent = String(n);
    }, 26);
  };

  return { svg, animate };
}

/** A labelled animated bar (dimension or signal). */
function bar(o: {
  label: string;
  score: number;
  band?: string;
  weightPct?: number | null;
  explanation?: string;
  context?: string | null;
}): { node: HTMLElement; animate: () => void } {
  const node = document.createElement("div");
  node.className = "bk-row";
  const w = Math.max(0, Math.min(100, o.score));
  const meta =
    (o.band ? `<span class="bk-band">${esc(o.band)}</span>` : "") +
    (o.weightPct != null ? `<span class="bk-wt">peso ${Math.round(o.weightPct)}%</span>` : "");
  node.innerHTML =
    `<div class="bk-rowhead"><span class="bk-lbl">${esc(o.label)}</span>` +
    `<span class="bk-score">${Math.round(o.score)}<small>/100</small></span></div>` +
    `<div class="bk-track"><div class="bk-fill"></div></div>` +
    (meta ? `<div class="bk-meta">${meta}</div>` : "") +
    (o.explanation ? `<div class="bk-expl">${esc(o.explanation)}</div>` : "") +
    (o.context ? `<div class="bk-ctx">${esc(o.context)}</div>` : "");
  const fill = node.querySelector<HTMLElement>(".bk-fill")!;
  const animate = () => {
    if (reduceMotion()) {
      fill.style.width = `${w}%`;
      return;
    }
    fill.style.width = "0%";
    requestAnimationFrame(() => {
      fill.style.transition = "width 1s cubic-bezier(.2,.75,.2,1)";
      fill.style.width = `${w}%`;
    });
  };
  return { node, animate };
}

function renderCountry(container: HTMLElement, c: CountryEvidence): void {
  container.innerHTML = "";
  const tier = mosTier(num(c.mos));

  // MOS focus
  const hero = document.createElement("div");
  hero.className = "bk-hero";
  const gauge = speedometer(num(c.mos), { size: 260, big: true });
  const gwrap = document.createElement("div");
  gwrap.className = "bk-gaugewrap";
  gwrap.appendChild(gauge.svg);
  const gcap = document.createElement("div");
  gcap.className = "bk-gaugecap";
  gcap.innerHTML = `<span class="bk-mostag" style="color:${tier.color};border-color:${tier.border};background:${tier.bg}">${esc(c.mos_band ?? "")}</span>`;
  gwrap.appendChild(gcap);
  hero.appendChild(gwrap);
  const heroText = document.createElement("div");
  heroText.className = "bk-herotext";
  heroText.innerHTML =
    `<div class="bk-heroflag"><span class="fg">${flag(c.country)}</span>${esc(countryName(c.country))}</div>` +
    `<div class="bk-herolbl">MOS / 100</div>` +
    (c.mos_explanation ? `<p>${esc(c.mos_explanation)}</p>` : "");
  hero.appendChild(heroText);
  container.appendChild(hero);

  const animations: (() => void)[] = [gauge.animate];

  // dimensions
  const dimsWrap = document.createElement("div");
  dimsWrap.className = "bk-sec";
  dimsWrap.innerHTML = `<div class="bk-sectitle">${t("rep.dimensions")}</div>`;
  const dimsBody = document.createElement("div");
  dimsBody.className = "bk-bars";
  (c.dimensions ?? []).forEach((d) => {
    const b = bar({
      label: d.label,
      score: d.score,
      band: d.band,
      weightPct: d.weight != null ? d.weight * 100 : null,
      explanation: d.explanation,
    });
    dimsBody.appendChild(b.node);
    animations.push(b.animate);
  });
  dimsWrap.appendChild(dimsBody);
  container.appendChild(dimsWrap);

  // signals
  const sigWrap = document.createElement("div");
  sigWrap.className = "bk-sec";
  sigWrap.innerHTML = `<div class="bk-sectitle">${t("rep.signals")}</div>`;
  const sigBody = document.createElement("div");
  sigBody.className = "bk-bars";
  (c.signals ?? []).forEach((s) => {
    const b = bar({
      label: s.label,
      score: s.score,
      band: s.band,
      explanation: s.explanation,
      context: s.context,
    });
    sigBody.appendChild(b.node);
    animations.push(b.animate);
  });
  sigWrap.appendChild(sigBody);
  container.appendChild(sigWrap);

  // run all animations on the next frame so they start from zero
  requestAnimationFrame(() => animations.forEach((a) => a()));
}

function closeModal(): void {
  const existing = document.getElementById("bk-overlay");
  if (existing) existing.remove();
  document.removeEventListener("keydown", onKey);
}

function onKey(e: KeyboardEvent): void {
  if (e.key === "Escape") closeModal();
}

/** Open the breakdown modal for an analysis request id. */
export async function openAnalysisModal(id: string): Promise<void> {
  closeModal();
  const overlay = document.createElement("div");
  overlay.id = "bk-overlay";
  overlay.className = "bk-overlay";
  overlay.innerHTML =
    `<div class="bk-panel" role="dialog" aria-modal="true">` +
    `<button class="bk-close" aria-label="Close">✕</button>` +
    `<div class="bk-state mono"><span class="bk-spin"></span>${esc(t("rep.loading"))}</div>` +
    `<div class="bk-content" style="display:none"></div>` +
    `</div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) closeModal();
  });
  overlay.querySelector(".bk-close")!.addEventListener("click", closeModal);
  document.addEventListener("keydown", onKey);

  let a: AnalysisStatusResponse;
  try {
    a = await getAnalysis(id);
  } catch (err) {
    const state = overlay.querySelector(".bk-state") as HTMLElement;
    state.textContent = err instanceof Error ? err.message : "Failed to load.";
    return;
  }

  const state = overlay.querySelector(".bk-state") as HTMLElement;
  const content = overlay.querySelector(".bk-content") as HTMLElement;

  if (!isTerminalStatus(a.status)) {
    state.textContent = `${t("dock.running")}…`;
    return;
  }
  if (a.status.toLowerCase() === "failed") {
    state.textContent = a.error_message ?? "Analysis failed.";
    return;
  }

  const packet = a.breakdown;
  const countries = (packet?.countries ?? [])
    .slice()
    .sort((x, y) => (num(y.mos) ?? -1) - (num(x.mos) ?? -1));

  // header
  const header = document.createElement("div");
  header.className = "bk-header";
  header.innerHTML =
    `<h2>${esc(a.canonical_title ?? "Product")}</h2>` +
    (packet?.period_key ? `<div class="bk-when mono">${t("rep.period")} ${esc(packet.period_key)}</div>` : "") +
    (a.user_prompt ? `<div class="bk-asked"><b>${t("rep.youasked")}:</b> ${esc(a.user_prompt)}</div>` : "");
  content.appendChild(header);

  if (countries.length === 0) {
    state.textContent = "No scored markets in this analysis.";
    return;
  }

  // country tabs
  const tabs = document.createElement("div");
  tabs.className = "bk-tabs";
  const detail = document.createElement("div");
  detail.className = "bk-detail";
  countries.forEach((c, i) => {
    const tab = document.createElement("button");
    tab.className = "bk-tab" + (i === 0 ? " on" : "");
    tab.innerHTML = `<span class="fg">${flag(c.country)}</span>${esc(countryName(c.country))} <b>${num(c.mos) !== null ? Math.round(num(c.mos)!) : "—"}</b>`;
    tab.addEventListener("click", () => {
      tabs.querySelectorAll(".bk-tab").forEach((el) => el.classList.remove("on"));
      tab.classList.add("on");
      renderCountry(detail, c);
    });
    tabs.appendChild(tab);
  });
  content.appendChild(tabs);
  content.appendChild(detail);

  // narrative
  if (a.explanation && a.explanation.trim()) {
    const nsec = document.createElement("div");
    nsec.className = "bk-sec bk-narrative";
    nsec.innerHTML = `<div class="bk-sectitle">${t("rep.narrative")}</div>`;
    a.explanation
      .split(/\n\s*\n/)
      .map((p) => p.trim())
      .filter(Boolean)
      .forEach((p) => {
        const para = document.createElement("p");
        para.textContent = p;
        nsec.appendChild(para);
      });
    content.appendChild(nsec);
  }

  state.style.display = "none";
  content.style.display = "block";
  renderCountry(detail, countries[0]);
}
