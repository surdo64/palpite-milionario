from io import BytesIO
from zipfile import ZipFile

from palpiteiro.estrategia import generate_bet, generate_bets
import json

from palpiteiro.historico import (
    _backfill_history_from_api,
    _merge_cached_history,
    _parse_api_history_entries,
    _request_bytes,
    StatisticsStore,
    build_statistics,
    parse_history_rows,
    parse_xlsx_rows,
)
from palpiteiro.loterias import LOTTERIES


def test_parse_xlsx_rows_lida_com_shared_string_e_inline_string() -> None:
    buffer = BytesIO()
    with ZipFile(buffer, "w") as workbook:
        workbook.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
              <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
              <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
              <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>
            </Types>
            """,
        )
        workbook.writestr(
            "xl/workbook.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
              xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
              <sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets>
            </workbook>
            """,
        )
        workbook.writestr(
            "xl/sharedStrings.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <si><t>Concurso</t></si>
              <si><t>Bola1</t></si>
            </sst>
            """,
        )
        workbook.writestr(
            "xl/worksheets/sheet1.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
              <sheetData>
                <row r="1">
                  <c r="A1" t="s"><v>0</v></c>
                  <c r="B1" t="s"><v>1</v></c>
                </row>
                <row r="2">
                  <c r="A2"><v>1</v></c>
                  <c r="B2" t="inlineStr"><is><t>07</t></is></c>
                </row>
              </sheetData>
            </worksheet>
            """,
        )
    content = buffer.getvalue()

    rows = parse_xlsx_rows(content)

    assert rows[0][:2] == ["Concurso", "Bola1"]
    assert rows[1][:2] == ["1", "07"]


def test_parse_history_rows_para_dupla_sena_duplica_os_dois_sorteios() -> None:
    rows = [
        [
            "Concurso",
            "Bola1 sorteio 1",
            "Bola2 sorteio 1",
            "Bola3 sorteio 1",
            "Bola4 Sorteio 1",
            "Bola5 sorteio 1",
            "Bola6 sorteio 1",
            "Bola1 sorteio 2",
            "Bola2 sorteio 2",
            "Bola3 sorteio 2",
            "Bola4 Sorteio 2",
            "Bola5 sorteio 2",
            "Bola6 sorteio 2",
        ],
        ["1", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"],
    ]

    records = parse_history_rows("dupla-sena", rows)

    assert records == [
        {"numbers": (1, 2, 3, 4, 5, 6)},
        {"numbers": (7, 8, 9, 10, 11, 12)},
    ]


class FakeStore:
    def __init__(self) -> None:
        self.payload = {
            "estatisticas": {
                "numbers": {str(number): 1.0 for number in range(1, 61)},
                "special": None,
                "total_registros": 10,
            }
        }
        self.payload["estatisticas"]["numbers"]["10"] = 500.0
        self.payload["estatisticas"]["numbers"]["20"] = 450.0
        self.payload["estatisticas"]["numbers"]["30"] = 400.0
        self.payload["estatisticas"]["numbers"]["40"] = 350.0
        self.payload["estatisticas"]["numbers"]["50"] = 300.0
        self.payload["estatisticas"]["numbers"]["60"] = 250.0

    def get_statistics(self, slug: str) -> dict[str, object]:
        return self.payload


def test_generate_bet_usa_estatisticas_quando_disponivel() -> None:
    bet = generate_bet("mega-sena", FakeStore(), profile="conservador")

    numbers = bet["numbers"]
    assert isinstance(numbers, tuple)
    assert len(numbers) == 6
    assert all(1 <= number <= 60 for number in numbers)


def test_generate_bets_em_fechamento_gera_lote_sem_repeticao_total() -> None:
    bets = generate_bets("mega-sena", 4, FakeStore(), profile="fechamento")

    assert len(bets) == 4
    rendered = {bet["numbers"] for bet in bets}
    assert len(rendered) >= 2


def test_parse_api_history_entries_para_dupla_sena_monta_dois_sorteios() -> None:
    payload = {
        "numero": 2946,
        "dataApuracao": "17/04/2026",
        "listaDezenas": ["12", "19", "29", "33", "34", "44"],
        "listaDezenasSegundoSorteio": ["11", "20", "32", "35", "44", "50"],
    }

    entries = _parse_api_history_entries("dupla-sena", payload)

    assert entries == [
        {"concurso": "2946", "data_sorteio": "17/04/2026", "numbers": (12, 19, 29, 33, 34, 44)},
        {"concurso": "2946", "data_sorteio": "17/04/2026", "numbers": (11, 20, 32, 35, 44, 50)},
    ]


def test_backfill_history_from_api_completa_concursos_faltantes(monkeypatch) -> None:
    history = [
        {"concurso": "2964", "data_sorteio": "24/01/2026", "numbers": (3, 9, 15, 17, 30, 60)},
    ]
    responses = {
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena": {
            "numero": 2966,
            "dataApuracao": "31/01/2026",
            "dataProximoConcurso": "01/02/2026",
            "valorEstimadoProximoConcurso": 3500000.0,
            "listaDezenas": ["01", "02", "03", "04", "05", "06"],
        },
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/2965": {
            "numero": 2965,
            "dataApuracao": "27/01/2026",
            "listaDezenas": ["01", "20", "22", "23", "35", "57"],
        },
        "https://servicebus2.caixa.gov.br/portaldeloterias/api/megasena/2966": {
            "numero": 2966,
            "dataApuracao": "31/01/2026",
            "listaDezenas": ["07", "08", "09", "10", "11", "12"],
        },
    }

    monkeypatch.setattr(
        "palpiteiro.historico._request_bytes",
        lambda url: json.dumps(responses[url]).encode("utf-8"),
    )

    merged, current = _backfill_history_from_api(LOTTERIES["mega-sena"], history)

    assert current["numero"] == 2966
    assert [item["concurso"] for item in merged] == ["2964", "2965", "2966"]
    assert merged[-1]["numbers"] == (7, 8, 9, 10, 11, 12)


def test_merge_cached_history_reaproveita_concursos_ja_complementados() -> None:
    parsed = [
        {"concurso": "2964", "data_sorteio": "24/01/2026", "numbers": (3, 9, 15, 17, 30, 60)},
    ]
    cached = [
        {"concurso": "2964", "data_sorteio": "24/01/2026", "numbers": (3, 9, 15, 17, 30, 60)},
        {"concurso": "2965", "data_sorteio": "27/01/2026", "numbers": (1, 20, 22, 23, 35, 57)},
        {"concurso": "2966", "data_sorteio": "31/01/2026", "numbers": (7, 8, 9, 10, 11, 12)},
    ]

    merged = _merge_cached_history(parsed, cached)

    assert [item["concurso"] for item in merged] == ["2964", "2965", "2966"]


def test_build_statistics_aceita_historico_vindo_do_cache_json() -> None:
    statistics = build_statistics(
        "mega-sena",
        [
            {"numbers": [1, 2, 3, 4, 5, 6]},
            {"numbers": (7, 8, 9, 10, 11, 12)},
        ],
    )

    assert statistics["total_registros"] == 2
    assert statistics["numbers"]["1"] > 1.0


def test_request_bytes_repete_falhas_transitorias(monkeypatch) -> None:
    calls: list[str] = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b"ok"

    def fake_urlopen(_request, timeout: int):
        assert timeout == 30
        calls.append("call")
        if len(calls) < 3:
            raise TimeoutError("temporario")
        return FakeResponse()

    monkeypatch.setattr("palpiteiro.historico.urlopen", fake_urlopen)
    monkeypatch.setattr("palpiteiro.historico.time.sleep", lambda _seconds: None)

    assert _request_bytes("https://example.test") == b"ok"
    assert len(calls) == 3


def test_refresh_all_preserva_loteria_atualizada_quando_outra_falha(monkeypatch) -> None:
    store = StatisticsStore.__new__(StatisticsStore)
    old_lotofacil = {"historico": [{"concurso": "1"}]}
    store.data = {
        "updated_at": "01/01/2026 00:00:00",
        "loterias": {"lotofacil": old_lotofacil},
    }
    saved: list[dict[str, object]] = []

    def fake_refresh(slug, _config, _latest, _progress=None):
        if slug == "lotofacil":
            raise TimeoutError("API indisponivel")
        return {"historico": [{"concurso": "2"}]}

    monkeypatch.setattr(
        "palpiteiro.historico.LOTTERIES",
        {
            "mega-sena": LOTTERIES["mega-sena"],
            "lotofacil": LOTTERIES["lotofacil"],
        },
    )
    monkeypatch.setattr("palpiteiro.historico._latest_result_dates", lambda: {})
    monkeypatch.setattr(store, "_refresh_lottery", fake_refresh)
    monkeypatch.setattr(store, "save_cache", lambda: saved.append(dict(store.data)))

    result = store.refresh_all()

    assert result.ok is False
    assert result.used_cache is True
    assert "Atualizacao parcial: 1 de 2" in result.message
    assert "Lotofacil: API indisponivel" in result.message
    assert store.data["loterias"]["mega-sena"]["historico"][0]["concurso"] == "2"
    assert store.data["loterias"]["lotofacil"] is old_lotofacil
    assert len(saved) == 1
