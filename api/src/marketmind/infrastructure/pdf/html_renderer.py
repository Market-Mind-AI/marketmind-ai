"""HTML report renderer — the offline default ``PdfRenderer``.

Renders an :class:`OpportunityReport` to a styled, self-contained HTML document
and returns it as UTF-8 bytes. No third-party dependency: this is the offline
fallback so the ``GET /report.pdf`` endpoint always returns something viewable.
For true PDF bytes, :class:`WeasyPrintPdfRenderer` reuses this HTML.

Exported as both ``HtmlReportRenderer`` (task brief) and ``HtmlPdfRenderer``
(authoritative contract) — same adapter.
"""

from __future__ import annotations

import html

from marketmind.application.ports.ports import PdfRenderer
from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.report import OpportunityReport

_STYLE = """
  :root { --ink:#1f2933; --muted:#52606d; --accent:#2563eb; --line:#e4e7eb; }
  * { box-sizing: border-box; }
  body { font-family: -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
         color: var(--ink); margin: 0; padding: 2.5rem; line-height: 1.5; }
  .wrap { max-width: 720px; margin: 0 auto; }
  h1 { font-size: 1.6rem; margin: 0 0 .25rem; }
  h2 { font-size: 1.05rem; margin: 1.75rem 0 .5rem; border-bottom: 1px solid var(--line);
       padding-bottom: .25rem; }
  .verdict { font-size: 1.15rem; font-weight: 600; color: var(--accent); }
  .muted { color: var(--muted); font-size: .85rem; }
  table { width: 100%; border-collapse: collapse; margin-top: .5rem; }
  th, td { text-align: left; padding: .4rem .5rem; border-bottom: 1px solid var(--line);
           font-size: .9rem; vertical-align: top; }
  th { color: var(--muted); font-weight: 600; }
  ul { margin: .5rem 0 0; padding-left: 1.2rem; }
  .band { font-size: 1.2rem; font-weight: 600; }
  footer { margin-top: 2rem; color: var(--muted); font-size: .75rem; }
"""


def _esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def render_report_html(report: OpportunityReport, analysis: Analysis) -> str:
    """Build the full HTML document string for a report."""
    markets_rows = (
        "\n".join(
            f"<tr><td>{_esc(m.country_name)} ({_esc(m.country_code)})</td>"
            f"<td>{m.score:.0f}/100</td><td>{_esc(m.rationale)}</td></tr>"
            for m in report.markets
        )
        or '<tr><td colspan="3" class="muted">No markets ranked.</td></tr>'
    )

    recs = "\n".join(f"<li>{_esc(r)}</li>" for r in report.recommendations)
    recs_block = f"<ul>{recs}</ul>" if recs else '<p class="muted">None.</p>'

    cites = (
        "\n".join(
            f"<tr><td>{_esc(c.source)}</td><td>{_esc(c.detail)}</td>"
            f"<td>{_esc(c.as_of)}</td></tr>"
            for c in report.citations
        )
        or '<tr><td colspan="3" class="muted">No citations.</td></tr>'
    )

    pb = report.price_band
    score_line = ""
    if analysis.score is not None:
        score_line = (
            f'<p class="muted">Market Opportunity Score: '
            f"{analysis.score.total:.1f}/100 ({_esc(analysis.score.tier)})</p>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>MarketMind Report — {_esc(analysis.id)}</title>
<style>{_STYLE}</style></head>
<body><div class="wrap">
  <h1>MarketMind AI — Opportunity Report</h1>
  <p class="verdict">{_esc(report.verdict)}</p>
  {score_line}
  <p>{_esc(report.summary)}</p>

  <h2>Target markets</h2>
  <table><thead><tr><th>Market</th><th>Score</th><th>Rationale</th></tr></thead>
  <tbody>{markets_rows}</tbody></table>

  <h2>Pricing</h2>
  <p class="band">{_esc(pb.currency)} {_esc(pb.low)} – {_esc(pb.high)}</p>
  <p class="muted">{_esc(pb.note)}</p>

  <h2>Timing</h2>
  <p><strong>{_esc(report.launch_window.label)}</strong> —
  {_esc(report.launch_window.peak_note)}</p>

  <h2>Recommendations</h2>
  {recs_block}

  <h2>Citations</h2>
  <table><thead><tr><th>Source</th><th>Detail</th><th>As of</th></tr></thead>
  <tbody>{cites}</tbody></table>

  <footer>Analysis {_esc(analysis.id)} · generated {_esc(analysis.created_at.isoformat())}</footer>
</div></body></html>"""


class HtmlReportRenderer(PdfRenderer):
    """Renders the report to styled HTML bytes (the offline default)."""

    def __init__(self) -> None:
        pass

    async def render(self, report: OpportunityReport, analysis: Analysis) -> bytes:
        return render_report_html(report, analysis).encode("utf-8")


# Contract alias: the authoritative contract names this ``HtmlPdfRenderer``.
HtmlPdfRenderer = HtmlReportRenderer
