from __future__ import annotations

import html
import json
import os
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Callable
import unicodedata
from urllib.parse import quote
from urllib.request import Request, urlopen
from zipfile import ZipFile
import xml.etree.ElementTree as ET

from palpiteiro.loterias import LOTTERIES, MONTHS, LotteryConfig


API_BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias"
LATEST_RESULTS_URL = f"{API_BASE_URL}/api/home/ultimos-resultados"
XML_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}


@dataclass(frozen=True)
class SyncResult:
    ok: bool
    used_cache: bool
    message: str
    updated_at: str | None = None


def format_currency(value: object) -> str:
    if value in (None, ""):
        return "nao informado"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    rendered = f"{amount:,.2f}"
    rendered = rendered.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R${rendered}"


def _cache_dir() -> Path:
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    base_dir = Path(xdg_data_home) if xdg_data_home else Path.home() / ".local" / "share"
    return base_dir / "palpite-milionario"


def _cache_file() -> Path:
    return _cache_dir() / "estatisticas.json"


def _request_bytes(url: str, attempts: int = 3) -> bytes:
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=30) as response:
                return response.read()
        except Exception as error:
            last_error = error
            if attempt + 1 < attempts:
                time.sleep(0.25 * (2**attempt))

    assert last_error is not None
    raise last_error


def _column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    value = 0
    for character in letters:
        value = value * 26 + (ord(character.upper()) - 64)
    return value - 1


def parse_xlsx_rows(content: bytes) -> list[list[str | None]]:
    workbook = ZipFile(BytesIO(content))

    shared_strings: list[str] = []
    if "xl/sharedStrings.xml" in workbook.namelist():
        shared_root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
        for item in shared_root.findall("a:si", XML_NS):
            shared_strings.append("".join(node.text or "" for node in item.findall(".//a:t", XML_NS)))

    sheet_root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
    rows: list[list[str | None]] = []

    for row in sheet_root.findall(".//a:sheetData/a:row", XML_NS):
        values: list[str | None] = []
        current_index = -1

        for cell in row.findall("a:c", XML_NS):
            reference = cell.attrib.get("r")
            index = _column_index(reference) if reference else current_index + 1
            while len(values) <= index:
                values.append(None)
            current_index = index

            cell_type = cell.attrib.get("t")
            if cell_type == "s":
                raw = cell.findtext("a:v", default="", namespaces=XML_NS)
                values[index] = shared_strings[int(raw)] if raw else ""
                continue

            if cell_type == "inlineStr":
                values[index] = "".join(node.text or "" for node in cell.findall(".//a:t", XML_NS))
                continue

            values[index] = cell.findtext("a:v", default="", namespaces=XML_NS)

        rows.append(values)

    return rows


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if normalized == "" or normalized == "-":
        return None
    return int(normalized)


def _normalize_key(value: str) -> str:
    normalized = html.unescape(value).strip()
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(character for character in decomposed if not unicodedata.combining(character)).lower()


def _normalize_month_label(value: str) -> str:
    normalized_key = _normalize_key(value)
    lookup = {_normalize_key(month): month for month in MONTHS}
    return lookup.get(normalized_key, html.unescape(value).strip().title())


def _parse_standard_rows(headers: dict[str, int], rows: list[list[str | None]], picks: int) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    ball_headers = [f"Bola{index}" for index in range(1, picks + 1)]
    for row in rows:
        numbers = tuple(
            number
            for number in (_to_int(row[headers[header]]) for header in ball_headers if header in headers)
            if number is not None
        )
        if numbers:
            parsed.append({"numbers": numbers})
    return parsed


def _parse_dupla_sena_rows(headers: dict[str, int], rows: list[list[str | None]]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    first_headers = [f"Bola{index} sorteio 1" if index != 4 else "Bola4 Sorteio 1" for index in range(1, 7)]
    second_headers = [f"Bola{index} sorteio 2" if index != 4 else "Bola4 Sorteio 2" for index in range(1, 7)]
    for row in rows:
        first_draw = tuple(
            number
            for number in (_to_int(row[headers[header]]) for header in first_headers if header in headers)
            if number is not None
        )
        second_draw = tuple(
            number
            for number in (_to_int(row[headers[header]]) for header in second_headers if header in headers)
            if number is not None
        )
        if first_draw:
            parsed.append({"numbers": first_draw})
        if second_draw:
            parsed.append({"numbers": second_draw})
    return parsed


def _parse_mais_milionaria_rows(headers: dict[str, int], rows: list[list[str | None]]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    ball_headers = [f"Bola{index}" for index in range(1, 7)]
    trevo_headers = ["Trevo1", "Trevo2"]
    for row in rows:
        numbers = tuple(
            number
            for number in (_to_int(row[headers[header]]) for header in ball_headers if header in headers)
            if number is not None
        )
        trevos = tuple(
            number
            for number in (_to_int(row[headers[header]]) for header in trevo_headers if header in headers)
            if number is not None
        )
        if numbers and trevos:
            parsed.append({"numbers": numbers, "special": trevos})
    return parsed


def _parse_dia_de_sorte_rows(headers: dict[str, int], rows: list[list[str | None]]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    ball_headers = [f"Bola{index}" for index in range(1, 8)]
    for row in rows:
        numbers = tuple(
            number
            for number in (_to_int(row[headers[header]]) for header in ball_headers if header in headers)
            if number is not None
        )
        month_label: str | None = None
        if "Mês da Sorte" in headers:
            raw_month = row[headers["Mês da Sorte"]]
            month_value: int | None = None
            if isinstance(raw_month, str):
                normalized_month = raw_month.strip()
                if normalized_month.isdigit():
                    month_value = int(normalized_month)
            elif raw_month is not None:
                month_value = _to_int(raw_month)
            if month_value is not None and 1 <= month_value <= len(MONTHS):
                month_label = MONTHS[month_value - 1]
            elif isinstance(raw_month, str) and raw_month.strip():
                month_label = _normalize_month_label(raw_month)

        if numbers and month_label is not None:
            parsed.append({"numbers": numbers, "special": (month_label,)})
    return parsed


def _parse_supersete_rows(headers: dict[str, int], rows: list[list[str | None]]) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    column_headers = [f"Coluna {index}" for index in range(1, 8)]
    for row in rows:
        columns = tuple(
            (_to_int(row[headers[header]]),)
            for header in column_headers
            if header in headers and _to_int(row[headers[header]]) is not None
        )
        if len(columns) == 7:
            parsed.append({"columns": columns})
    return parsed


def parse_history_rows(slug: str, rows: list[list[str | None]]) -> list[dict[str, object]]:
    headers = {str(value): index for index, value in enumerate(rows[0]) if value not in (None, "")}
    data_rows = rows[1:]

    if slug in {"mega-sena", "lotofacil", "quina"}:
        return _parse_standard_rows(headers, data_rows, LOTTERIES[slug].picks)
    if slug == "lotomania":
        return _parse_standard_rows(headers, data_rows, 20)
    if slug == "dupla-sena":
        return _parse_dupla_sena_rows(headers, data_rows)
    if slug == "mais-milionaria":
        return _parse_mais_milionaria_rows(headers, data_rows)
    if slug == "dia-de-sorte":
        return _parse_dia_de_sorte_rows(headers, data_rows)
    if slug == "supersete":
        return _parse_supersete_rows(headers, data_rows)

    raise ValueError(f"Sem parser configurado para {slug}.")


def _occurrence_weight(index: int, total: int) -> float:
    if total == 0:
        return 1.0
    if index >= total - 10:
        return 3.5
    if index >= total - 30:
        return 2.5
    return 1.0


def build_statistics(slug: str, records: list[dict[str, object]]) -> dict[str, object]:
    config = LOTTERIES[slug]

    if config.columns:
        column_weights: list[dict[str, float]] = [{str(digit): 1.0 for digit in range(10)} for _ in range(7)]
        total = len(records)
        for index, record in enumerate(records):
            weight = _occurrence_weight(index, total)
            columns = _tuple_from_sequence(record.get("columns"))
            for column_index, digits in enumerate(columns):
                digits = _tuple_from_sequence(digits)
                if not digits:
                    continue
                digit = digits[0]
                column_weights[column_index][str(digit)] += 1.0 + weight
        return {"columns": column_weights, "total_registros": len(records)}

    number_weights = {str(number): 1.0 for number in range(config.min_value, config.max_value + 1)}
    special_weights: dict[str, float] | None = None

    if config.special_values:
        special_weights = {value: 1.0 for value in config.special_values}
    elif config.special_min is not None and config.special_max is not None:
        special_weights = {
            str(value): 1.0 for value in range(config.special_min, config.special_max + 1)
        }

    total = len(records)
    for index, record in enumerate(records):
        weight = _occurrence_weight(index, total)
        numbers = _tuple_from_sequence(record.get("numbers"))
        for number in numbers:
            number_weights[str(number)] += 1.0 + weight

        if special_weights is None:
            continue

        special_values = _tuple_from_sequence(record.get("special"))
        for value in special_values:
            special_weights[str(value)] += 1.0 + weight

    return {
        "numbers": number_weights,
        "special": special_weights,
        "total_registros": len(records),
    }


def _latest_result_dates() -> dict[str, str]:
    payload = json.loads(_request_bytes(LATEST_RESULTS_URL).decode("utf-8"))
    return {
        "mega-sena": payload["megasena"],
        "lotofacil": payload["lotofacil"],
        "quina": payload["quina"],
        "mais-milionaria": payload["maisMilionaria"],
        "lotomania": payload["lotomania"],
        "dupla-sena": payload["duplasena"],
        "dia-de-sorte": payload["diaDeSorte"],
        "supersete": payload["superSete"],
    }


def _lottery_result_url(api_path: str, contest: int | None = None) -> str:
    suffix = f"/{contest}" if contest is not None else ""
    return f"{API_BASE_URL}/api/{api_path}{suffix}"


def _simplify_record(slug: str, index: int, record: dict[str, object], rows: list[list[str | None]]) -> dict[str, object]:
    row_index = index + 1
    if slug == "dupla-sena":
        row_index = index // 2 + 1
    row = rows[row_index] if row_index < len(rows) else []
    concurso = row[0] if row and len(row) > 0 else None
    data_sorteio = row[1] if row and len(row) > 1 else None
    simplified: dict[str, object] = {
        "concurso": concurso,
        "data_sorteio": data_sorteio,
    }
    simplified.update(record)
    return simplified


def _parse_int_sequence(values: object) -> tuple[int, ...]:
    if not isinstance(values, list):
        return ()
    numbers: list[int] = []
    for value in values:
        parsed = _to_int(str(value))
        if parsed is not None:
            numbers.append(parsed)
    return tuple(numbers)


def _tuple_from_sequence(values: object) -> tuple[object, ...]:
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    return ()


def _parse_api_history_entries(slug: str, payload: dict[str, object]) -> list[dict[str, object]]:
    contest_number = payload.get("numero")
    draw_date = payload.get("dataApuracao")
    base: dict[str, object] = {
        "concurso": str(contest_number) if contest_number is not None else None,
        "data_sorteio": str(draw_date) if draw_date is not None else None,
    }

    if slug == "dupla-sena":
        entries: list[dict[str, object]] = []
        first_draw = _parse_int_sequence(payload.get("listaDezenas"))
        second_draw = _parse_int_sequence(payload.get("listaDezenasSegundoSorteio"))
        if first_draw:
            entries.append({**base, "numbers": first_draw})
        if second_draw:
            entries.append({**base, "numbers": second_draw})
        return entries

    if slug == "mais-milionaria":
        numbers = _parse_int_sequence(payload.get("listaDezenas"))
        trevos = _parse_int_sequence(payload.get("trevosSorteados"))
        if numbers and trevos:
            return [{**base, "numbers": numbers, "special": trevos}]
        return []

    if slug == "dia-de-sorte":
        numbers = _parse_int_sequence(payload.get("listaDezenas"))
        month_label = payload.get("nomeTimeCoracaoMesSorte")
        if isinstance(month_label, str) and month_label.strip() and numbers:
            return [{**base, "numbers": numbers, "special": (_normalize_month_label(month_label),)}]
        return []

    if slug == "supersete":
        digits = _parse_int_sequence(payload.get("listaDezenas"))
        if len(digits) == 7:
            return [{**base, "columns": tuple((digit,) for digit in digits)}]
        return []

    numbers = _parse_int_sequence(payload.get("listaDezenas"))
    if numbers:
        return [{**base, "numbers": numbers}]
    return []


def _highest_contest_number(history: list[dict[str, object]]) -> int:
    highest = 0
    for item in history:
        contest = item.get("concurso")
        if contest is None:
            continue
        try:
            highest = max(highest, int(str(contest)))
        except ValueError:
            continue
    return highest


def _history_identity(item: dict[str, object]) -> str:
    contest = str(item.get("concurso") or "")
    if "numbers" in item:
        values = item.get("numbers", ())
    elif "columns" in item:
        values = item.get("columns", ())
    else:
        values = item.get("special", ())
    return f"{contest}|{json.dumps(values, ensure_ascii=True, sort_keys=True)}"


def _merge_cached_history(
    parsed_history: list[dict[str, object]],
    cached_history: object,
) -> list[dict[str, object]]:
    if not isinstance(cached_history, list) or not cached_history:
        return parsed_history

    merged: list[dict[str, object]] = []
    seen: set[str] = set()

    for item in parsed_history:
        if not isinstance(item, dict):
            continue
        identity = _history_identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(item)

    for item in cached_history:
        if not isinstance(item, dict):
            continue
        identity = _history_identity(item)
        if identity in seen:
            continue
        seen.add(identity)
        merged.append(item)

    merged.sort(key=lambda item: (int(str(item.get("concurso") or 0)), _history_identity(item)))
    return merged


def _backfill_history_from_api(
    config: LotteryConfig,
    history: list[dict[str, object]],
    progress: Callable[[str], None] | None = None,
) -> tuple[list[dict[str, object]], dict[str, object]]:
    current_payload = json.loads(_request_bytes(_lottery_result_url(config.api_path)).decode("utf-8"))
    latest_contest = current_payload.get("numero")
    if not isinstance(latest_contest, int):
        return history, current_payload

    highest_contest = _highest_contest_number(history)
    if highest_contest >= latest_contest:
        return history, current_payload

    for contest in range(highest_contest + 1, latest_contest + 1):
        if progress is not None:
            progress(f"Complementando historico de {config.display_name}: concurso {contest}...")
        payload = json.loads(_request_bytes(_lottery_result_url(config.api_path, contest)).decode("utf-8"))
        entries = _parse_api_history_entries(config.slug, payload)
        if entries:
            history.extend(entries)

    return history, current_payload


class StatisticsStore:
    def __init__(self) -> None:
        self.data: dict[str, object] = {}
        self.cache_warning: str | None = None
        self._cache_write_blocked = False
        self.load_cache()

    def load_cache(self) -> None:
        cache_path = _cache_file()
        self.data = {"updated_at": None, "loterias": {}}
        try:
            raw = cache_path.read_bytes()
        except FileNotFoundError:
            return
        except OSError:
            self._cache_write_blocked = True
            self.cache_warning = "Não foi possível ler o cache local. O arquivo será preservado."
            return
        try:
            self.data = self._decode_cache(raw)
        except (ValueError, UnicodeError):
            # Preserve the exact original before allowing a subsequent refresh.
            try:
                with tempfile.NamedTemporaryFile(
                    dir=cache_path.parent, prefix="estatisticas-recuperacao-", suffix=".json", delete=False
                ) as backup:
                    backup.write(raw)
                    backup.flush()
                    os.fsync(backup.fileno())
            except OSError:
                self._cache_write_blocked = True
            self.cache_warning = "O cache local está inválido. Os resultados serão atualizados novamente."
            try:
                self.data = self._decode_cache(cache_path.with_suffix(".json.bak").read_bytes())
                self.cache_warning = "O cache local está inválido. Foi recuperada a última cópia válida."
            except (OSError, ValueError, UnicodeError):
                pass
            if self._cache_write_blocked:
                self.cache_warning += " A gravação foi bloqueada para preservar o arquivo original."

    @staticmethod
    def _decode_cache(raw: bytes) -> dict[str, object]:
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("loterias"), dict):
            raise ValueError("Estrutura do cache inválida.")
        return data

    @staticmethod
    def _atomic_write(destination: Path, content: bytes) -> None:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".estatisticas-", delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, destination)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def save_cache(self) -> None:
        if self._cache_write_blocked:
            raise OSError("Gravação bloqueada para preservar o cache original que não pôde ser lido ou copiado.")
        cache_path = _cache_file()
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(self.data, ensure_ascii=True, indent=2).encode("utf-8")
        try:
            previous = cache_path.read_bytes()
            self._decode_cache(previous)
        except (FileNotFoundError, ValueError, UnicodeError):
            pass
        else:
            self._atomic_write(cache_path.with_suffix(".json.bak"), previous)
        self._atomic_write(cache_path, content)

    def _refresh_lottery(
        self,
        slug: str,
        config: LotteryConfig,
        latest: object,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, object]:
        cached_entry = self.get_statistics(slug)
        cached_history = cached_entry.get("historico") if isinstance(cached_entry, dict) else None

        try:
            url = (
                f"{API_BASE_URL}/api/resultados/download?modalidade="
                f"{quote(config.api_modalidade)}"
            )
            rows = parse_xlsx_rows(_request_bytes(url))
            records = parse_history_rows(slug, rows)
            parsed_history = [
                _simplify_record(slug, index, record, rows)
                for index, record in enumerate(records)
            ]
        except Exception:
            if not isinstance(cached_history, list) or not cached_history:
                raise
            parsed_history = []

        history = _merge_cached_history(parsed_history, cached_history)
        history, current_result = _backfill_history_from_api(config, history, progress)
        latest_data = dict(latest) if isinstance(latest, dict) else {}
        if current_result.get("dataApuracao"):
            latest_data["dataApuracao"] = current_result.get("dataApuracao")
        if current_result.get("valorEstimadoProximoConcurso") is not None:
            latest_data["valorEstimadoProximoConcurso"] = current_result.get("valorEstimadoProximoConcurso")
        if current_result.get("dataProximoConcurso"):
            latest_data["dataProximoConcurso"] = current_result.get("dataProximoConcurso")
        if current_result.get("numeroConcursoProximo") is not None:
            latest_data["numeroConcursoProximo"] = current_result.get("numeroConcursoProximo")
        if current_result.get("numero") is not None:
            latest_data["numero"] = current_result.get("numero")

        stats_records = [
            {
                key: value
                for key, value in item.items()
                if key not in {"concurso", "data_sorteio"}
            }
            for item in history
        ]
        return {
            "estatisticas": build_statistics(slug, stats_records),
            "data_apuracao": latest_data.get("dataApuracao"),
            "proximo_premio": latest_data.get("valorEstimadoProximoConcurso"),
            "data_proximo_concurso": latest_data.get("dataProximoConcurso"),
            "concurso_proximo": latest_data.get("numeroConcursoProximo"),
            "concurso_atual": latest_data.get("numero"),
            "historico": history,
        }

    def has_statistics(self, slug: str) -> bool:
        lotteries = self.data.get("loterias", {})
        return isinstance(lotteries, dict) and slug in lotteries

    def get_statistics(self, slug: str) -> dict[str, object] | None:
        lotteries = self.data.get("loterias", {})
        if not isinstance(lotteries, dict):
            return None
        statistics = lotteries.get(slug)
        return statistics if isinstance(statistics, dict) else None

    def refresh_all(self, progress: ProgressCallback | None = None) -> SyncResult:
        try:
            latest_results = _latest_result_dates()
        except Exception:
            latest_results = {}

        lotteries = self.data.get("loterias")
        if not isinstance(lotteries, dict):
            lotteries = {}
        self.data["loterias"] = lotteries
        total = len(LOTTERIES)
        updated: list[str] = []
        failures: list[str] = []

        for index, (slug, config) in enumerate(LOTTERIES.items(), start=1):
            if progress is not None:
                progress(index - 1, total, f"Atualizando {config.display_name}...")
            try:
                lotteries[slug] = self._refresh_lottery(
                    slug,
                    config,
                    latest_results.get(slug, {}),
                    None if progress is None else lambda message, current=index - 1: progress(current, total, message),
                )
                updated_at = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                self.data["updated_at"] = updated_at
                self.save_cache()
                updated.append(config.display_name)
                if progress is not None:
                    progress(index, total, f"{config.display_name} atualizado.")
            except Exception as error:
                error_text = str(error).strip() or type(error).__name__
                failures.append(f"{config.display_name}: {error_text}")
                if progress is not None:
                    progress(index, total, f"Falha em {config.display_name}: {error_text}")

        updated_at_value = self.data.get("updated_at")
        updated_at = str(updated_at_value) if updated_at_value else None
        if not failures:
            return SyncResult(True, False, "Resultados oficiais atualizados.", updated_at)
        details = "; ".join(failures)
        if updated:
            return SyncResult(
                False,
                True,
                f"Atualizacao parcial: {len(updated)} de {total} loterias atualizadas. Falhas: {details}",
                updated_at,
            )
        if lotteries:
            return SyncResult(False, True, f"Falha na atualizacao online. Cache preservado. Falhas: {details}", updated_at)
        return SyncResult(False, False, f"Falha ao obter resultados oficiais: {details}")
ProgressCallback = Callable[[int, int, str], None]
