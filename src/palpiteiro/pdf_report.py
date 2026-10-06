from __future__ import annotations

import json
import tempfile
from datetime import datetime
from html import escape
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

from palpiteiro import __version__
from palpiteiro.loterias import LotteryConfig

PDF_DATA_PREFIX = "palpite-milionario:"


def create_pdf_report(
    lottery: LotteryConfig,
    bets: list[str],
    *,
    structured_bets: list[dict[str, object]],
    quantity: int,
    price_per_game: str,
    total_price: str,
    prize_info: str,
) -> Path:
    """Generate a private temporary PDF, including data for later checking."""
    directory = Path(tempfile.mkdtemp(prefix="palpite-"))
    destination = directory / "relatorio.pdf"
    try:
        styles = getSampleStyleSheet()
        body = ParagraphStyle("Palpites", parent=styles["BodyText"], fontSize=11, leading=16)
        doc = SimpleDocTemplate(
            str(destination), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
            topMargin=18 * mm, bottomMargin=20 * mm,
            title=f"Palpite Milionário - {lottery.display_name}", author="Palpite Milionário",
        )
        story = [
            Paragraph("Palpite Milionário", styles["Title"]),
            Paragraph(escape(lottery.display_name), styles["Heading2"]),
            Paragraph(f"Gerado em {datetime.now():%d/%m/%Y %H:%M:%S}", body),
            Paragraph(f"Quantidade: {quantity} | Valor por jogo: {escape(price_per_game)}", body),
            Paragraph(f"Total: {escape(total_price)}", body),
            Paragraph(escape(prize_info), body),
            Spacer(1, 6 * mm),
        ]
        if bets:
            rows = [[Paragraph("Jogo", body), Paragraph("Palpite", body)]]
            rows.extend([Paragraph(str(index), body), Paragraph(escape(bet), body)]
                        for index, bet in enumerate(bets, 1))
            table = LongTable(rows, colWidths=[18 * mm, doc.width - 18 * mm], repeatRows=1)
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e7eee9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#d3dcd5")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]))
            story.append(table)
        else:
            story.append(Paragraph("Nenhum palpite disponível.", body))
        story.extend([Spacer(1, 6 * mm), Paragraph(
            "Os palpites não garantem premiação. Confira os resultados oficiais da CAIXA.", body
        )])
        payload = PDF_DATA_PREFIX + json.dumps(
            {"lottery_slug": lottery.slug, "bets": structured_bets}, ensure_ascii=True
        )

        def page_footer(canvas, document):
            canvas.setKeywords(payload)
            canvas.saveState()
            canvas.setFont("Helvetica", 9)
            canvas.drawString(18 * mm, 12 * mm, f"Palpite Milionário | Versão {__version__}")
            canvas.drawRightString(A4[0] - 18 * mm, 12 * mm, f"Página {document.page}")
            canvas.restoreState()

        doc.build(story, onFirstPage=page_footer, onLaterPages=page_footer)
        destination.chmod(0o600)
        return destination
    except Exception:
        destination.unlink(missing_ok=True)
        directory.rmdir()
        raise
