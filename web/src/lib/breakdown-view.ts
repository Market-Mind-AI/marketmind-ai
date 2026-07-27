// Rich MOS breakdown modal. Given an analysis request id, fetches the full
// evidence packet and renders it: a big animated MOS speedometer per country
// (the focus), then every dimension subscore and deterministic signal grouped
// as animated speedometers (see grouped-scores), plus the LLM narrative. Charts
// re-animate every time the modal opens or the country tab changes.

import {
  getAnalysis,
  fetchCountries,
  isTerminalStatus,
  num,
  flag,
  countryName,
  mosTier,
  type AnalysisStatusResponse,
  type CountryEvidence,
} from "./api";
import { speedometer } from "./speedometer";
import { renderGroupedScores } from "./grouped-scores";
import { t } from "./i18n";

let escEl: HTMLElement | null = null;
function esc(s: string): string {
  if (!escEl) escEl = document.createElement("div");
  escEl.textContent = s ?? "";
  return escEl.innerHTML;
}

function renderCountry(container: HTMLElement, c: CountryEvidence): void {
  container.innerHTML = "";
  const tier = mosTier(num(c.mos));

  // MOS focus
  const hero = document.createElement("div");
  hero.className = "bk-hero";
  const gauge = speedometer(num(c.mos), { size: 260, className: "big" });
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
    (c.mos_explanation ? `<p>${esc(c.mos_explanation)}</p>` : "") +
    (c.demand_confidence === "low"
      ? `<div class="bk-warn">⚠ ${esc(c.demand_confidence_note ?? "")}</div>`
      : "");
  hero.appendChild(heroText);
  container.appendChild(hero);

  // grouped deterministic scores (dimension bar + nested signal bars)
  const groups = document.createElement("div");
  groups.className = "gs-root bk-groups";
  container.appendChild(groups);
  const animateGroups = renderGroupedScores(groups, c);

  requestAnimationFrame(() => {
    gauge.animate();
    animateGroups();
  });
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
    await fetchCountries().catch(() => []); // names/flags resolve from this cache
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
