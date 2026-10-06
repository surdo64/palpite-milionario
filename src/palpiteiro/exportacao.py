from __future__ import annotations

import json
import os
from datetime import datetime
from html import escape
from pathlib import Path

from palpiteiro import __version__
from palpiteiro.loterias import LotteryConfig

APP_NAME = "Palpite Milionário"
APP_DIR_NAME = "PalpiteMilionario"
APP_SLUG = "palpite-milionario"
REPORT_DATA_ID = "palpite-milionario-report-data"
LEGACY_REPORT_DATA_ID = "palpiteiro-report-data"
SIDECAR_SUFFIX = ".palpite-milionario.txt"
LEGACY_SIDECAR_SUFFIX = ".palpiteiro.txt"
TEXT_MARKER = "--- PALPITE-MILIONARIO-DADOS ---"
LEGACY_TEXT_MARKER = "--- PALPITEIRO-DADOS ---"


def _column_layout(lottery: LotteryConfig, bets: list[str]) -> tuple[int, int]:
    longest = max((len(bet) for bet in bets), default=0)

    if lottery.slug == "lotomania":
        return 3, 4
    if lottery.slug == "supersete" or longest >= 90:
        return 1, 1
    if lottery.slug == "mega-sena":
        if longest >= 35:
            return 2, 2
        return 4, 5
    if lottery.slug == "quina":
        if longest >= 35:
            return 2, 2
        return 4, 5
    if lottery.slug == "dupla-sena":
        if longest >= 35:
            return 2, 2
        return 4, 5
    if lottery.slug == "lotofacil":
        if longest >= 50:
            return 1, 2
        return 2, 2
    if lottery.slug == "dia-de-sorte":
        if longest >= 45:
            return 1, 2
        return 2, 2
    if lottery.slug in {"mais-milionaria", "dia-de-sorte"}:
        return 2, 2
    if longest >= 55:
        return 2, 2
    if longest >= 40:
        return 3, 4
    return 4, 5


def _format_html_bet(lottery: LotteryConfig, bet: str) -> str:
    if lottery.slug == "lotomania":
        numbers = bet.split()
        rows = [" ".join(numbers[index : index + 10]) for index in range(0, len(numbers), 10)]
        return "<br>".join(escape(row) for row in rows)
    return escape(bet)


def build_html_report(
    lottery: LotteryConfig,
    bets: list[str],
    *,
    structured_bets: list[dict[str, object]] | None = None,
    quantity: int,
    price_per_game: str,
    total_price: str,
    prize_info: str,
) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    screen_columns, print_columns = _column_layout(lottery, bets)
    items = "\n".join(
        f"<li><span class='label'>Jogo {index}</span><span class='bet'>{_format_html_bet(lottery, bet)}</span></li>"
        for index, bet in enumerate(bets, start=1)
    )
    embedded_payload = json.dumps(
        {
            "lottery_slug": lottery.slug,
            "bets": structured_bets or [],
        },
        ensure_ascii=False,
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{APP_NAME} - {escape(lottery.display_name)}</title>
  <style>
    :root {{
      --bg: #f3efe5;
      --ink: #173524;
      --accent: #d8c6a2;
      --panel: #fffdf8;
      --muted: #5a625d;
      --line: #d9d2c5;
      --screen-columns: {screen_columns};
      --print-columns: {print_columns};
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: linear-gradient(180deg, #ede4d2 0%, var(--bg) 26%, #f8f5ee 100%);
      color: var(--ink);
      font-family: "Segoe UI", sans-serif;
    }}
    .page {{
      max-width: 980px;
      margin: 0 auto;
      padding: 18px 14px 20px;
    }}
    .mega-sena-long.page-wide .page,
    .mega-sena-long .page,
    .quina-long.page-wide .page,
    .quina-long .page,
    .dupla-sena-long.page-wide .page,
    .dupla-sena-long .page {{
      max-width: 1180px;
    }}
    .hero {{
      background: var(--ink);
      color: #f9f4e7;
      border-radius: 18px;
      padding: 18px 22px;
      box-shadow: 0 20px 40px rgba(23, 53, 36, 0.18);
    }}
    .hero h1 {{
      margin: 0;
      font-size: 28px;
    }}
    .hero p {{
      margin: 6px 0 0;
      color: #dce7de;
      font-size: 13px;
    }}
    .meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }}
    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      box-shadow: 0 10px 24px rgba(78, 67, 46, 0.08);
    }}
    .card .title {{
      display: block;
      color: var(--muted);
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      margin-bottom: 4px;
    }}
    .card .value {{
      font-size: 18px;
      font-weight: 700;
    }}
    .prize {{
      margin-top: 10px;
      padding: 10px 12px;
      background: #f6f0e2;
      border-left: 6px solid var(--accent);
      border-radius: 14px;
      font-size: 13px;
    }}
    .list {{
      margin: 12px 0 0;
      padding: 0;
      list-style: none;
      column-count: var(--screen-columns);
      column-gap: 6px;
    }}
    .list li {{
      display: grid;
      grid-template-columns: 54px 1fr;
      gap: 4px;
      padding: 7px 8px;
      margin: 0 0 6px;
      background: rgba(255, 253, 248, 0.9);
      border: 1px solid var(--line);
      border-radius: 10px;
      break-inside: avoid;
      page-break-inside: avoid;
    }}
    .label {{
      font-weight: 700;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }}
    .bet {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      line-height: 1.25;
      white-space: nowrap;
    }}
    .lotomania-long .bet {{
      white-space: normal;
      line-height: 1.35;
    }}
    .footer {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 11px;
    }}
    @media print {{
      @page {{
        margin: 8mm;
      }}
      body {{
        background: #fff;
      }}
      .page {{
        max-width: none;
        padding: 0;
      }}
      .hero {{
        box-shadow: none;
        border-radius: 10px;
        padding: 10px 12px;
      }}
      .card {{
        box-shadow: none;
        border-radius: 10px;
        padding: 8px 10px;
      }}
      .hero h1 {{
        font-size: 20px;
      }}
      .hero p {{
        font-size: 11px;
      }}
      .meta {{
        gap: 4px;
        margin-top: 8px;
      }}
      .card .title {{
        font-size: 9px;
      }}
      .card .value {{
        font-size: 14px;
      }}
      .prize {{
        margin-top: 8px;
        padding: 6px 8px;
        font-size: 10px;
        border-radius: 10px;
      }}
      .list {{
        margin-top: 8px;
        column-count: var(--print-columns);
        column-gap: 4px;
      }}
      .list li {{
        grid-template-columns: 48px 1fr;
        gap: 3px;
        padding: 4px 6px;
        margin: 0 0 4px;
        border-radius: 8px;
      }}
      .label {{
        font-size: 9px;
        white-space: nowrap;
      }}
      .bet {{
        font-size: 9px;
        line-height: 1.05;
      }}
      .lotofacil-long .list li {{
        grid-template-columns: 34px 1fr;
        gap: 2px;
        padding: 3px 4px;
      }}
      .lotofacil-long .label {{
        font-size: 8px;
      }}
      .lotofacil-long .bet {{
        font-size: 8px;
        line-height: 1;
        letter-spacing: -0.02em;
      }}
      .dia-de-sorte-long .list li {{
        grid-template-columns: 34px 1fr;
        gap: 2px;
        padding: 3px 4px;
      }}
      .dia-de-sorte-long .label {{
        font-size: 8px;
      }}
      .dia-de-sorte-long .bet {{
        font-size: 8px;
        line-height: 1;
        letter-spacing: -0.02em;
      }}
      .lotomania-long .bet {{
        font-size: 8px;
        line-height: 1.15;
      }}
      .lotomania-long .list li {{
        grid-template-columns: 34px 1fr;
        gap: 2px;
        padding: 3px 4px;
      }}
      .lotomania-long .label {{
        font-size: 8px;
      }}
      .footer {{
        margin-top: 8px;
        font-size: 8px;
      }}
    }}
  </style>
</head>
<body class="{'lotofacil-long' if lottery.slug == 'lotofacil' and max((len(bet) for bet in bets), default=0) >= 50 else ''}{' mega-sena-long' if lottery.slug == 'mega-sena' and max((len(bet) for bet in bets), default=0) >= 35 else ''}{' quina-long' if lottery.slug == 'quina' and max((len(bet) for bet in bets), default=0) >= 35 else ''}{' dupla-sena-long' if lottery.slug == 'dupla-sena' and max((len(bet) for bet in bets), default=0) >= 35 else ''}{' dia-de-sorte-long' if lottery.slug == 'dia-de-sorte' and max((len(bet) for bet in bets), default=0) >= 45 else ''}{' lotomania-long' if lottery.slug == 'lotomania' else ''}">
  <main class="page">
    <section class="hero">
      <h1>{escape(lottery.display_name)}</h1>
      <p>Palpites gerados pelo {APP_NAME} em {generated_at}</p>
    </section>
    <section class="meta">
      <article class="card">
        <span class="title">Quantidade</span>
        <span class="value">{quantity} jogo(s)</span>
      </article>
      <article class="card">
        <span class="title">Valor de referência por combinação</span>
        <span class="value">{escape(price_per_game)}</span>
      </article>
      <article class="card">
        <span class="title">Total</span>
        <span class="value">{escape(total_price)}</span>
      </article>
    </section>
    <section class="prize">{escape(prize_info)}</section>
    <ol class="list">
      {items}
    </ol>
    <script type="application/json" id="{REPORT_DATA_ID}">{escape(embedded_payload)}</script>
    <footer class="footer">
      Versão {__version__}. Este relatório foi gerado para visualização e impressão.
    </footer>
  </main>
</body>
</html>
"""


def save_html_report(content: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination


def default_html_report_path(lottery: LotteryConfig) -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    base_dir = base_dir / APP_SLUG
    export_dir = base_dir / "exportacoes"
    filename = f"{APP_SLUG}-{lottery.slug}-{datetime.now().strftime('%Y%m%d-%H%M%S')}.html"
    return export_dir / filename


def sidecar_txt_path(path: Path) -> Path:
    return path.with_suffix(SIDECAR_SUFFIX)


def legacy_sidecar_txt_path(path: Path) -> Path:
    return path.with_suffix(LEGACY_SIDECAR_SUFFIX)


def save_sidecar_report(
    lottery: LotteryConfig,
    structured_bets: list[dict[str, object]],
    destination: Path,
) -> Path:
    payload = {
        "lottery_slug": lottery.slug,
        "bets": structured_bets,
    }
    txt_path = sidecar_txt_path(destination)
    txt_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return txt_path


def build_text_report(
    lottery: LotteryConfig,
    bets: list[str],
    *,
    structured_bets: list[dict[str, object]],
    quantity: int,
    price_per_game: str,
    total_price: str,
    prize_info: str,
    profile: str,
) -> str:
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    lines = [
        APP_NAME,
        f"Loteria: {lottery.display_name}",
        f"Gerado em: {generated_at}",
        f"Quantidade: {quantity} jogo(s)",
        f"Preco por jogo: {price_per_game}",
        f"Total: {total_price}",
        f"Perfil estatistico: {profile}",
        prize_info,
        "",
    ]
    for index, bet in enumerate(bets, start=1):
        lines.append(f"Jogo {index}: {bet}")

    payload = json.dumps(
        {
            "lottery_slug": lottery.slug,
            "bets": structured_bets,
        },
        ensure_ascii=False,
        indent=2,
    )
    lines.extend(["", TEXT_MARKER, payload])
    return "\n".join(lines)


def save_text_report(content: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(content, encoding="utf-8")
    return destination
