"""WeasyPrint PDF renderer (optional dependency).

Renders the same styled HTML as :class:`HtmlReportRenderer` to real PDF bytes
via WeasyPrint. ``weasyprint`` is imported lazily inside ``render`` so this
module — and the whole app — imports without the optional ``pdf`` extra
installed. The offline default remains :class:`HtmlReportRenderer`.
"""

from __future__ import annotations

import asyncio

from marketmind.application.ports.ports import PdfRenderer
from marketmind.domain.model.analysis import Analysis
from marketmind.domain.model.report import OpportunityReport
from marketmind.infrastructure.pdf.html_renderer import render_report_html


class WeasyPrintPdfRenderer(PdfRenderer):
    """Renders the report to PDF bytes using WeasyPrint."""

    def __init__(self) -> None:
        pass

    async def render(self, report: OpportunityReport, analysis: Analysis) -> bytes:
        document_html = render_report_html(report, analysis)
        return await asyncio.to_thread(self._to_pdf, document_html)

    @staticmethod
    def _to_pdf(document_html: str) -> bytes:
        try:
            from weasyprint import HTML  # lazy: optional dependency
        except ImportError as exc:  # pragma: no cover - env-dependent
            raise NotImplementedError(
                "WeasyPrintPdfRenderer requires the optional 'weasyprint' "
                "dependency (install the 'pdf' extra); use HtmlReportRenderer "
                "offline."
            ) from exc
        return HTML(string=document_html).write_pdf()
