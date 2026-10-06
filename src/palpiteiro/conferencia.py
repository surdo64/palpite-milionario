from __future__ import annotations

import json
import re
from dataclasses import dataclass
from html import unescape
from pathlib import Path

from palpiteiro.exportacao import (
    LEGACY_REPORT_DATA_ID,
    LEGACY_SIDECAR_SUFFIX,
    LEGACY_TEXT_MARKER,
    REPORT_DATA_ID,
    SIDECAR_SUFFIX,
    TEXT_MARKER,
    legacy_sidecar_txt_path,
    sidecar_txt_path,
)
from palpiteiro.loterias import LOTTERIES, LotteryConfig, get_lottery


EMBEDDED_REPORT_PATTERN = re.compile(
    rf'<script type="application/json" id="(?:{REPORT_DATA_ID}|{LEGACY_REPORT_DATA_ID})">\s*(.*?)\s*</script>',
    re.DOTALL,
)
TITLE_PATTERN = re.compile(r"<title>(?:Palpite Milionário|Palpite Milionario|Palpiteiro) - (.*?)</title>", re.DOTALL)
BET_PATTERN = re.compile(r"<span class='bet'>(.*?)</span>", re.DOTALL)
TEXT_PAYLOAD_PATTERN = re.compile(
    rf"(?:{re.escape(TEXT_MARKER)}|{re.escape(LEGACY_TEXT_MARKER)})\s*(\{{.*\}})\s*$",
    re.DOTALL,
)

STANDARD_PRIZE_LABELS: dict[str, dict[int, str]] = {
    "mega-sena": {4: "Quadra", 5: "Quina", 6: "Sena"},
    "lotofacil": {
        11: "11 acertos",
        12: "12 acertos",
        13: "13 acertos",
        14: "14 acertos",
        15: "15 acertos",
    },
    "quina": {2: "Duque", 3: "Terno", 4: "Quadra", 5: "Quina"},
    "lotomania": {
        0: "0 acertos",
        15: "15 acertos",
        16: "16 acertos",
        17: "17 acertos",
        18: "18 acertos",
        19: "19 acertos",
        20: "20 acertos",
    },
}

MAIS_MILIONARIA_PRIZE_LABELS: dict[tuple[int, int], str] = {
    (6, 2): "Faixa 1 — 6 números e 2 trevos",
    (6, 1): "Faixa 2 — 6 números e 1 trevo",
    (6, 0): "Faixa 2 — 6 números e nenhum trevo",
    (5, 2): "Faixa 3 — 5 números e 2 trevos",
    (5, 1): "Faixa 4 — 5 números e 1 trevo",
    (5, 0): "Faixa 4 — 5 números e nenhum trevo",
    (4, 2): "Faixa 5 — 4 números e 2 trevos",
    (4, 1): "Faixa 6 — 4 números e 1 trevo",
    (4, 0): "Faixa 6 — 4 números e nenhum trevo",
    (3, 2): "Faixa 7 — 3 números e 2 trevos",
    (3, 1): "Faixa 8 — 3 números e 1 trevo",
    (2, 2): "Faixa 9 — 2 números e 2 trevos",
    (2, 1): "Faixa 10 — 2 números e 1 trevo",
}

DIA_DE_SORTE_PRIZE_LABELS: dict[int, str] = {
    4: "4 acertos",
    5: "5 acertos",
    6: "6 acertos",
    7: "7 acertos",
}

SUPERSETE_PRIZE_LABELS: dict[int, str] = {
    3: "3 colunas",
    4: "4 colunas",
    5: "5 colunas",
    6: "6 colunas",
    7: "7 colunas",
}

DUPLA_SENA_PRIZE_LABELS: dict[int, str] = {
    3: "Terno",
    4: "Quadra",
    5: "Quina",
    6: "Sena",
}


@dataclass(frozen=True)
class LoadedReport:
    lottery: LotteryConfig
    bets: list[dict[str, object]]
    source: Path


def _lottery_by_display_name(name: str) -> LotteryConfig:
    normalized = unescape(name).strip().lower()
    for config in LOTTERIES.values():
        if config.display_name.lower() == normalized:
            return config
    return get_lottery(normalized)


def _parse_rendered_bet(lottery: LotteryConfig, rendered: str) -> dict[str, object]:
    text = unescape(rendered).strip()
    if lottery.columns:
        columns: list[tuple[int, ...]] = []
        for part in text.split(" | "):
            _, values = part.split(": ", 1)
            columns.append(tuple(int(value) for value in values.split()))
        return {"columns": tuple(columns)}

    if " | " not in text:
        return {"numbers": tuple(int(value) for value in text.split())}

    numbers_text, special_text = text.split(" | ", 1)
    bet: dict[str, object] = {"numbers": tuple(int(value) for value in numbers_text.split())}

    if lottery.special_values:
        _, values = special_text.split(": ", 1)
        bet["special"] = tuple(value.strip() for value in values.split(","))
    else:
        _, values = special_text.split(": ", 1)
        bet["special"] = tuple(int(value) for value in values.split())
    return bet


def load_saved_report(path: Path) -> LoadedReport:
    if path.suffix.lower() == ".pdf":
        preferred = sidecar_txt_path(path)
        legacy = legacy_sidecar_txt_path(path)
        if preferred.exists():
            path = preferred
        elif legacy.exists():
            path = legacy
        else:
            from pypdf import PdfReader
            from pypdf.errors import PdfReadError
            from palpiteiro.pdf_report import PDF_DATA_PREFIX

            try:
                metadata = PdfReader(path).metadata
                payload_text = str((metadata or {}).get("/Keywords", ""))
                if not payload_text.startswith(PDF_DATA_PREFIX):
                    raise ValueError("PDF sem dados de conferência incorporados.")
                payload = json.loads(payload_text[len(PDF_DATA_PREFIX):])
                lottery = get_lottery(str(payload["lottery_slug"]))
                bets = payload["bets"]
                if not isinstance(bets, list) or not all(isinstance(bet, dict) for bet in bets):
                    raise ValueError("Dados de palpites inválidos.")
                return LoadedReport(lottery=lottery, bets=bets, source=path)
            except (PdfReadError, ValueError, KeyError, TypeError) as error:
                raise ValueError(
                    f"PDF sem dados válidos de conferência. Para PDFs antigos, mantenha o arquivo {SIDECAR_SUFFIX} ao lado dele."
                ) from error

    if path.suffix.lower() == ".txt" or path.name.endswith(SIDECAR_SUFFIX) or path.name.endswith(LEGACY_SIDECAR_SUFFIX):
        content = path.read_text(encoding="utf-8")
        match = TEXT_PAYLOAD_PATTERN.search(content)
        payload_text = match.group(1) if match else content
        payload = json.loads(payload_text)
        lottery = get_lottery(str(payload["lottery_slug"]))
        bets = payload.get("bets", [])
        if isinstance(bets, list):
            return LoadedReport(lottery=lottery, bets=bets, source=path)
        raise ValueError("Arquivo TXT de palpites invalido.")

    content = path.read_text(encoding="utf-8")
    embedded = EMBEDDED_REPORT_PATTERN.search(content)
    if embedded:
        payload = json.loads(unescape(embedded.group(1)))
        lottery = get_lottery(str(payload["lottery_slug"]))
        bets = payload.get("bets", [])
        if isinstance(bets, list):
            return LoadedReport(lottery=lottery, bets=bets, source=path)

    title_match = TITLE_PATTERN.search(content)
    if not title_match:
        raise ValueError("Nao foi possivel identificar a loteria no HTML informado.")

    lottery = _lottery_by_display_name(title_match.group(1))
    rendered_bets = [unescape(match.group(1)) for match in BET_PATTERN.finditer(content)]
    if not rendered_bets:
        raise ValueError("Nao foi possivel localizar palpites no HTML informado.")

    return LoadedReport(
        lottery=lottery,
        bets=[_parse_rendered_bet(lottery, item) for item in rendered_bets],
        source=path,
    )


def _compare_standard_bet(
    bet: dict[str, object],
    result: dict[str, object],
) -> tuple[str, int]:
    bet_numbers = set(int(value) for value in bet["numbers"])
    result_numbers = set(int(value) for value in result["numbers"])
    matches = sorted(bet_numbers & result_numbers)
    return f"{len(matches)} acerto(s) [{', '.join(str(value) for value in matches) if matches else '-'}]", len(matches)


def _compare_mais_milionaria(bet: dict[str, object], result: dict[str, object]) -> tuple[str, float]:
    bet_numbers = set(int(value) for value in bet["numbers"])
    result_numbers = set(int(value) for value in result["numbers"])
    bet_special = set(int(value) for value in bet.get("special", ()))
    result_special = set(int(value) for value in result.get("special", ()))
    number_matches = sorted(bet_numbers & result_numbers)
    special_matches = sorted(bet_special & result_special)
    score = len(number_matches) + (len(special_matches) / 10)
    return (
        f"{len(number_matches)} numero(s) e {len(special_matches)} trevo(s) "
        f"[numeros: {', '.join(str(value) for value in number_matches) if number_matches else '-'} | "
        f"trevos: {', '.join(str(value) for value in special_matches) if special_matches else '-'}]",
        score,
    )


def _compare_dia_de_sorte(bet: dict[str, object], result: dict[str, object]) -> tuple[str, float]:
    bet_numbers = set(int(value) for value in bet["numbers"])
    result_numbers = set(int(value) for value in result["numbers"])
    number_matches = sorted(bet_numbers & result_numbers)
    month_match = bet.get("special", ()) == result.get("special", ())
    score = len(number_matches) + (0.1 if month_match else 0.0)
    return (
        f"{len(number_matches)} numero(s) e mes da sorte {'OK' if month_match else 'nao'} "
        f"[numeros: {', '.join(str(value) for value in number_matches) if number_matches else '-'}]",
        score,
    )


def _compare_supersete(bet: dict[str, object], result: dict[str, object]) -> tuple[str, int]:
    bet_columns = bet.get("columns", ())
    result_columns = result.get("columns", ())
    hits: list[str] = []
    for index, (bet_digits, result_digits) in enumerate(zip(bet_columns, result_columns), start=1):
        bet_values = set(int(value) for value in bet_digits)
        draw_digit = int(result_digits[0])
        if draw_digit in bet_values:
            hits.append(str(index))
    return f"{len(hits)} coluna(s) certa(s) [{', '.join(hits) if hits else '-'}]", len(hits)


def _compare_dupla_sena(bet: dict[str, object], results: list[dict[str, object]]) -> tuple[str, float]:
    comparisons: list[tuple[str, int]] = []
    best_score = 0
    for index, result in enumerate(results, start=1):
        rendered, score = _compare_standard_bet(bet, result)
        best_score = max(best_score, score)
        comparisons.append((f"{index}o sorteio: {rendered}", score))
    return " | ".join(item[0] for item in comparisons), float(best_score)


def _matching_numbers(bet: dict[str, object], result: dict[str, object]) -> int:
    bet_numbers = {int(value) for value in bet.get("numbers", ())}
    result_numbers = {int(value) for value in result.get("numbers", ())}
    return len(bet_numbers & result_numbers)


def _matching_special_numbers(bet: dict[str, object], result: dict[str, object]) -> int:
    bet_special = {int(value) for value in bet.get("special", ())}
    result_special = {int(value) for value in result.get("special", ())}
    return len(bet_special & result_special)


def _matching_supersete_columns(bet: dict[str, object], result: dict[str, object]) -> int:
    bet_columns = bet.get("columns", ())
    result_columns = result.get("columns", ())
    matches = 0
    for bet_digits, result_digits in zip(bet_columns, result_columns):
        bet_values = {int(value) for value in bet_digits}
        if result_digits and int(result_digits[0]) in bet_values:
            matches += 1
    return matches


def _prize_labels(
    lottery: LotteryConfig,
    bet: dict[str, object],
    results: list[dict[str, object]],
) -> tuple[str, ...]:
    primary_result = results[0]

    if lottery.slug in STANDARD_PRIZE_LABELS:
        matches = _matching_numbers(bet, primary_result)
        label = STANDARD_PRIZE_LABELS[lottery.slug].get(matches)
        return (label,) if label else ()

    if lottery.slug == "mais-milionaria":
        number_matches = _matching_numbers(bet, primary_result)
        trevo_matches = _matching_special_numbers(bet, primary_result)
        label = MAIS_MILIONARIA_PRIZE_LABELS.get((number_matches, trevo_matches))
        return (label,) if label else ()

    if lottery.slug == "dia-de-sorte":
        labels: list[str] = []
        number_label = DIA_DE_SORTE_PRIZE_LABELS.get(_matching_numbers(bet, primary_result))
        if number_label:
            labels.append(number_label)
        if tuple(bet.get("special", ())) == tuple(primary_result.get("special", ())):
            labels.append("Mês da Sorte")
        return tuple(labels)

    if lottery.slug == "supersete":
        label = SUPERSETE_PRIZE_LABELS.get(_matching_supersete_columns(bet, primary_result))
        return (label,) if label else ()

    if lottery.slug == "dupla-sena":
        labels = []
        for index, result in enumerate(results, start=1):
            label = DUPLA_SENA_PRIZE_LABELS.get(_matching_numbers(bet, result))
            if label:
                labels.append(f"{index}º sorteio: {label}")
        return tuple(labels)

    return ()


def compare_saved_report(
    report: LoadedReport,
    contest: int,
    statistics: dict[str, object],
) -> str:
    history = statistics.get("historico")
    if not isinstance(history, list):
        raise ValueError("Historico oficial indisponivel para conferência.")

    contest_entries = [
        item for item in history
        if isinstance(item, dict) and str(item.get("concurso")) == str(contest)
    ]
    if not contest_entries:
        raise ValueError(f"Concurso {contest} nao encontrado no historico oficial de {report.lottery.display_name}.")

    result_line = " | ".join(report.lottery.format_bet(item) for item in contest_entries)
    lines = [
        "Conferência de palpites",
        f"Loteria: {report.lottery.display_name}",
        f"Arquivo: {report.source}",
        f"Concurso: {contest}",
        f"Resultado oficial: {result_line}",
        f"Total de palpites analisados: {len(report.bets)}",
        "",
    ]

    summary: dict[str, int] = {}
    details: list[tuple[bool, float, str]] = []
    primary_result = contest_entries[0]
    awarded_bets = 0

    for index, bet in enumerate(report.bets, start=1):
        if report.lottery.slug == "mais-milionaria":
            rendered, score = _compare_mais_milionaria(bet, primary_result)
        elif report.lottery.slug == "dia-de-sorte":
            rendered, score = _compare_dia_de_sorte(bet, primary_result)
        elif report.lottery.slug == "supersete":
            rendered, score = _compare_supersete(bet, primary_result)
        elif report.lottery.slug == "dupla-sena":
            rendered, score = _compare_dupla_sena(bet, contest_entries)
        else:
            rendered, score = _compare_standard_bet(bet, primary_result)

        prizes = _prize_labels(report.lottery, bet, contest_entries)
        if prizes:
            awarded_bets += 1
            prize_status = f"PREMIADO — {'; '.join(prizes)}"
        else:
            prize_status = "NÃO PREMIADO"

        summary[rendered.split(" [", 1)[0]] = summary.get(rendered.split(" [", 1)[0], 0) + 1
        details.append(
            (
                bool(prizes),
                score,
                f"Jogo {index}: {report.lottery.format_bet(bet)} -> "
                f"{rendered} -> {prize_status}",
            )
        )

    if awarded_bets:
        lines.append("Resultado da conferência: CONTEMPLADO COM ALGUMA PREMIAÇÃO")
    else:
        lines.append("Resultado da conferência: NÃO CONTEMPLADO")
    lines.append(f"Jogos com alguma premiação: {awarded_bets} de {len(report.bets)}")
    lines.append(
        "Observação: a faixa foi identificada pelas regras da modalidade; "
        "confirme o valor no resultado oficial da CAIXA."
    )
    lines.extend(["", "Resumo:"])

    for key, total in sorted(summary.items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"- {key}: {total}")

    lines.extend(["", "Detalhes dos jogos:"])
    awarded_details = sorted(
        (item for item in details if item[0]),
        key=lambda item: item[1],
        reverse=True,
    )
    other_details = sorted(
        (item for item in details if not item[0]),
        key=lambda item: item[1],
        reverse=True,
    )
    visible_details = awarded_details + other_details[:max(0, 30 - len(awarded_details))]
    for _, _, detail in visible_details:
        lines.append(detail)

    return "\n".join(lines)
