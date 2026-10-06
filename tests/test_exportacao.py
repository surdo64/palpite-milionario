import os
from pathlib import Path

import pytest

from palpiteiro.conferencia import LoadedReport, compare_saved_report, load_saved_report
from palpiteiro.exportacao import (
    build_html_report,
    build_text_report,
    default_html_report_path,
    save_html_report,
    save_sidecar_report,
    save_text_report,
    sidecar_txt_path,
)
from palpiteiro.loterias import LOTTERIES


def _compare_bet(
    slug: str,
    bet: dict[str, object],
    results: list[dict[str, object]],
) -> str:
    contest = 100
    history = [{"concurso": str(contest), **result} for result in results]
    report = LoadedReport(
        lottery=LOTTERIES[slug],
        bets=[bet],
        source=Path("palpites.txt"),
    )
    return compare_saved_report(report, contest, {"historico": history})


def test_build_html_report_inclui_dados_principais() -> None:
    lottery = LOTTERIES["mega-sena"]

    content = build_html_report(
        lottery,
        ["01 02 03 04 05 06", "07 08 09 10 11 12"],
        structured_bets=[
            {"numbers": [1, 2, 3, 4, 5, 6]},
            {"numbers": [7, 8, 9, 10, 11, 12]},
        ],
        quantity=2,
        price_per_game="R$6,00",
        total_price="R$12,00",
        prize_info="Proximo premio estimado: R$70.000.000,00 | Proximo concurso: 23/04/2026",
    )

    assert "<title>Palpite Milionário - Mega-Sena</title>" in content
    assert "R$12,00" in content
    assert "Jogo 2" in content
    assert "Proximo premio estimado: R$70.000.000,00" in content
    assert "palpite-milionario-report-data" in content


def test_save_html_report_grava_arquivo(tmp_path: Path) -> None:
    destination = tmp_path / "palpite.html"

    saved = save_html_report("<html></html>", destination)

    assert saved == destination
    assert destination.read_text(encoding="utf-8") == "<html></html>"


def test_default_html_report_path_usa_diretorio_xdg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))

    path = default_html_report_path(LOTTERIES["quina"])

    assert path.parent == tmp_path / "palpite-milionario" / "exportacoes"
    assert path.name.startswith("palpite-milionario-quina-")
    assert path.suffix == ".html"


def test_save_sidecar_report_grava_txt_pareado(tmp_path: Path) -> None:
    pdf_path = tmp_path / "meus-palpites.pdf"

    saved = save_sidecar_report(
        LOTTERIES["mega-sena"],
        [{"numbers": [1, 2, 3, 4, 5, 6]}],
        pdf_path,
    )

    assert saved == sidecar_txt_path(pdf_path)
    assert saved.read_text(encoding="utf-8")


def test_load_saved_report_e_compare_saved_report(tmp_path: Path) -> None:
    lottery = LOTTERIES["mega-sena"]
    destination = tmp_path / "palpite.html"
    content = build_html_report(
        lottery,
        ["01 02 03 04 05 06", "10 11 12 13 14 15"],
        structured_bets=[
            {"numbers": [1, 2, 3, 4, 5, 6]},
            {"numbers": [10, 11, 12, 13, 14, 15]},
        ],
        quantity=2,
        price_per_game="R$6,00",
        total_price="R$12,00",
        prize_info="Proximo premio estimado: R$70.000.000,00 | Proximo concurso: 2999 em 23/04/2026",
    )
    save_html_report(content, destination)

    report = load_saved_report(destination)
    result = compare_saved_report(
        report,
        2998,
        {
            "historico": [
                {"concurso": "2998", "numbers": [1, 2, 3, 4, 5, 6]},
            ]
        },
    )

    assert report.lottery.slug == "mega-sena"
    assert "Total de palpites analisados: 2" in result
    assert "Jogo 1" in result
    assert "6 acerto(s)" in result


@pytest.mark.parametrize(
    ("slug", "bet", "results", "expected_prize"),
    [
        (
            "mega-sena",
            {"numbers": [1, 2, 3, 4, 5, 6]},
            [{"numbers": [1, 2, 3, 4, 5, 6]}],
            "Sena",
        ),
        (
            "lotofacil",
            {"numbers": list(range(1, 16))},
            [{"numbers": list(range(1, 16))}],
            "15 acertos",
        ),
        (
            "quina",
            {"numbers": [1, 2, 3, 4, 5]},
            [{"numbers": [1, 2, 3, 4, 5]}],
            "Quina",
        ),
        (
            "mais-milionaria",
            {"numbers": [1, 2, 3, 4, 5, 6], "special": [1, 2]},
            [{"numbers": [1, 2, 3, 4, 5, 6], "special": [1, 2]}],
            "Faixa 1",
        ),
        (
            "lotomania",
            {"numbers": list(range(50))},
            [{"numbers": list(range(20))}],
            "20 acertos",
        ),
        (
            "dupla-sena",
            {"numbers": [1, 2, 3, 4, 5, 6]},
            [
                {"numbers": [1, 2, 3, 4, 5, 6]},
                {"numbers": [7, 8, 9, 10, 11, 12]},
            ],
            "1º sorteio: Sena",
        ),
        (
            "dia-de-sorte",
            {"numbers": [1, 2, 3, 4, 5, 6, 7], "special": ["Janeiro"]},
            [{"numbers": [1, 2, 3, 4, 5, 6, 7], "special": ["Janeiro"]}],
            "Mês da Sorte",
        ),
        (
            "supersete",
            {"columns": tuple((digit,) for digit in range(1, 8))},
            [{"columns": tuple((digit,) for digit in range(1, 8))}],
            "7 colunas",
        ),
    ],
)
def test_compare_saved_report_informa_premiacao_em_todas_as_loterias(
    slug: str,
    bet: dict[str, object],
    results: list[dict[str, object]],
    expected_prize: str,
) -> None:
    result = _compare_bet(slug, bet, results)

    assert "Resultado da conferência: CONTEMPLADO COM ALGUMA PREMIAÇÃO" in result
    assert "Jogos com alguma premiação: 1 de 1" in result
    assert "PREMIADO" in result
    assert expected_prize in result


@pytest.mark.parametrize(
    ("slug", "bet", "results"),
    [
        (
            "mega-sena",
            {"numbers": [1, 2, 3, 4, 5, 6]},
            [{"numbers": [7, 8, 9, 10, 11, 12]}],
        ),
        (
            "lotofacil",
            {"numbers": list(range(1, 16))},
            [{"numbers": list(range(11, 26))}],
        ),
        (
            "quina",
            {"numbers": [1, 2, 3, 4, 5]},
            [{"numbers": [5, 6, 7, 8, 9]}],
        ),
        (
            "mais-milionaria",
            {"numbers": [1, 2, 3, 4, 5, 6], "special": [1, 2]},
            [{"numbers": [6, 7, 8, 9, 10, 11], "special": [3, 4]}],
        ),
        (
            "lotomania",
            {"numbers": list(range(50))},
            [{"numbers": list(range(40, 60))}],
        ),
        (
            "dupla-sena",
            {"numbers": [1, 2, 3, 4, 5, 6]},
            [
                {"numbers": [5, 6, 7, 8, 9, 10]},
                {"numbers": [6, 7, 8, 9, 10, 11]},
            ],
        ),
        (
            "dia-de-sorte",
            {"numbers": [1, 2, 3, 4, 5, 6, 7], "special": ["Janeiro"]},
            [{"numbers": [5, 6, 7, 8, 9, 10, 11], "special": ["Fevereiro"]}],
        ),
        (
            "supersete",
            {"columns": tuple((digit,) for digit in range(1, 8))},
            [{"columns": ((1,), (2,), (8,), (9,), (0,), (0,), (0,))}],
        ),
    ],
)
def test_compare_saved_report_informa_quando_nao_ha_premiacao(
    slug: str,
    bet: dict[str, object],
    results: list[dict[str, object]],
) -> None:
    result = _compare_bet(slug, bet, results)

    assert "Resultado da conferência: NÃO CONTEMPLADO" in result
    assert "Jogos com alguma premiação: 0 de 1" in result
    assert "-> NÃO PREMIADO" in result


@pytest.mark.parametrize(
    ("slug", "bet", "results", "expected_prize"),
    [
        (
            "mega-sena",
            {"numbers": [1, 2, 3, 4, 20, 21]},
            [{"numbers": [1, 2, 3, 4, 5, 6]}],
            "Quadra",
        ),
        (
            "lotofacil",
            {"numbers": list(range(1, 12)) + [20, 21, 22, 23]},
            [{"numbers": list(range(1, 16))}],
            "11 acertos",
        ),
        (
            "quina",
            {"numbers": [1, 2, 20, 21, 22]},
            [{"numbers": [1, 2, 3, 4, 5]}],
            "Duque",
        ),
        (
            "mais-milionaria",
            {"numbers": [1, 2, 20, 21, 22, 23], "special": [1, 3]},
            [{"numbers": [1, 2, 3, 4, 5, 6], "special": [1, 2]}],
            "Faixa 10",
        ),
        (
            "lotomania",
            {"numbers": list(range(50))},
            [{"numbers": list(range(50, 70))}],
            "0 acertos",
        ),
        (
            "dupla-sena",
            {"numbers": [1, 2, 3, 20, 21, 22]},
            [
                {"numbers": [30, 31, 32, 33, 34, 35]},
                {"numbers": [1, 2, 3, 4, 5, 6]},
            ],
            "2º sorteio: Terno",
        ),
        (
            "dia-de-sorte",
            {"numbers": [20, 21, 22, 23, 24, 25, 26], "special": ["Janeiro"]},
            [{"numbers": [1, 2, 3, 4, 5, 6, 7], "special": ["Janeiro"]}],
            "Mês da Sorte",
        ),
        (
            "supersete",
            {"columns": ((1,), (2,), (3,), (8,), (8,), (8,), (8,))},
            [{"columns": ((1,), (2,), (3,), (4,), (5,), (6,), (7,))}],
            "3 colunas",
        ),
    ],
)
def test_compare_saved_report_reconhece_faixa_minima_de_premiacao(
    slug: str,
    bet: dict[str, object],
    results: list[dict[str, object]],
    expected_prize: str,
) -> None:
    result = _compare_bet(slug, bet, results)

    assert "CONTEMPLADO COM ALGUMA PREMIAÇÃO" in result
    assert expected_prize in result


def test_compare_saved_report_mantem_jogo_premiado_entre_os_detalhes() -> None:
    lottery = LOTTERIES["lotomania"]
    non_awarded_bets = [
        {"numbers": [*range(40), *range(50, 60)]}
        for _ in range(30)
    ]
    winning_bet = {"numbers": list(range(50))}
    report = LoadedReport(
        lottery=lottery,
        bets=[*non_awarded_bets, winning_bet],
        source=Path("palpites.txt"),
    )

    result = compare_saved_report(
        report,
        100,
        {"historico": [{"concurso": "100", "numbers": list(range(50, 70))}]},
    )

    assert "Jogo 31:" in result
    assert "0 acertos" in result
    assert "PREMIADO" in result


def test_load_saved_report_a_partir_do_pdf_busca_sidecar_txt(tmp_path: Path) -> None:
    pdf_path = tmp_path / "meus-palpites.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    save_sidecar_report(
        LOTTERIES["mega-sena"],
        [{"numbers": [1, 2, 3, 4, 5, 6]}],
        pdf_path,
    )

    report = load_saved_report(pdf_path)

    assert report.lottery.slug == "mega-sena"
    assert report.bets == [{"numbers": [1, 2, 3, 4, 5, 6]}]


def test_build_text_report_e_load_saved_report_em_txt(tmp_path: Path) -> None:
    destination = tmp_path / "palpites.txt"
    content = build_text_report(
        LOTTERIES["mega-sena"],
        ["01 02 03 04 05 06"],
        structured_bets=[{"numbers": [1, 2, 3, 4, 5, 6]}],
        quantity=1,
        price_per_game="R$6,00",
        total_price="R$6,00",
        prize_info="Proximo premio estimado: R$70.000.000,00",
        profile="equilibrado",
    )

    save_text_report(content, destination)
    report = load_saved_report(destination)

    assert "Palpite Milionário" in content
    assert "Jogo 1: 01 02 03 04 05 06" in content
    assert report.lottery.slug == "mega-sena"
    assert report.bets == [{"numbers": [1, 2, 3, 4, 5, 6]}]


def test_build_html_report_reduz_colunas_para_jogos_muito_longos() -> None:
    content = build_html_report(
        LOTTERIES["lotomania"],
        ["00 05 09 11 14 18 23 27 31 36 40 44 49 55 61 68 74 82 91 100"],
        structured_bets=[
            {"numbers": [0, 5, 9, 11, 14, 18, 23, 27, 31, 36, 40, 44, 49, 55, 61, 68, 74, 82, 91, 100]}
        ],
        quantity=1,
        price_per_game="R$3,00",
        total_price="R$3,00",
        prize_info="Teste",
    )

    assert "--screen-columns: 3;" in content
    assert "--print-columns: 4;" in content
    assert "lotomania-long" in content
    assert "<br>" in content
    assert "grid-template-columns: 34px 1fr;" in content
    assert "gap: 2px;" in content


def test_build_html_report_reduz_colunas_da_lotofacil() -> None:
    content = build_html_report(
        LOTTERIES["lotofacil"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 13 14 15"],
        structured_bets=[{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}],
        quantity=1,
        price_per_game="R$3,50",
        total_price="R$3,50",
        prize_info="Teste",
    )

    assert "--screen-columns: 2;" in content
    assert "--print-columns: 2;" in content


def test_build_html_report_reduz_lotofacil_muito_longa_para_uma_coluna() -> None:
    content = build_html_report(
        LOTTERIES["lotofacil"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 16 17 18 19 20"],
        structured_bets=[
            {"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]}
        ],
        quantity=1,
        price_per_game="R$54.264,00",
        total_price="R$54.264,00",
        prize_info="Teste",
    )

    assert "--screen-columns: 1;" in content
    assert "--print-columns: 2;" in content
    assert 'class="lotofacil-long"' in content


def test_build_html_report_reduz_mega_sena_longa() -> None:
    content = build_html_report(
        LOTTERIES["mega-sena"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 13 14 15"],
        structured_bets=[{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}],
        quantity=1,
        price_per_game="R$30.030,00",
        total_price="R$30.030,00",
        prize_info="Teste",
    )

    assert "--screen-columns: 2;" in content
    assert "--print-columns: 2;" in content
    assert "mega-sena-long" in content
    assert "max-width: 1180px;" in content


def test_build_html_report_reduz_quina_longa() -> None:
    content = build_html_report(
        LOTTERIES["quina"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 13 14 15"],
        structured_bets=[{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}],
        quantity=1,
        price_per_game="R$9.009,00",
        total_price="R$9.009,00",
        prize_info="Teste",
    )

    assert "--screen-columns: 2;" in content
    assert "--print-columns: 2;" in content
    assert "quina-long" in content
    assert "max-width: 1180px;" in content


def test_build_html_report_reduz_dupla_sena_longa() -> None:
    content = build_html_report(
        LOTTERIES["dupla-sena"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 13 14 15"],
        structured_bets=[{"numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]}],
        quantity=1,
        price_per_game="R$12.512,50",
        total_price="R$12.512,50",
        prize_info="Teste",
    )

    assert "--screen-columns: 2;" in content
    assert "--print-columns: 2;" in content
    assert "dupla-sena-long" in content
    assert "max-width: 1180px;" in content


def test_build_html_report_reduz_colunas_da_mais_milionaria() -> None:
    content = build_html_report(
        LOTTERIES["mais-milionaria"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 | Trevos: 1 2 3 4 5 6"],
        structured_bets=[{"numbers": [1, 2, 3], "special": [1, 2]}],
        quantity=1,
        price_per_game="R$6,00",
        total_price="R$6,00",
        prize_info="Teste",
    )

    assert "--screen-columns: 2;" in content
    assert "--print-columns: 2;" in content


def test_build_html_report_reduz_colunas_do_dia_de_sorte() -> None:
    content = build_html_report(
        LOTTERIES["dia-de-sorte"],
        ["01 02 03 04 05 06 07 08 09 10 11 12 13 14 15 | Mes da sorte: Setembro"],
        structured_bets=[{"numbers": [1, 2, 3], "special": ["Setembro"]}],
        quantity=1,
        price_per_game="R$2,50",
        total_price="R$2,50",
        prize_info="Teste",
    )

    assert "--screen-columns: 1;" in content
    assert "--print-columns: 2;" in content
    assert "dia-de-sorte-long" in content
    assert "grid-template-columns: 34px 1fr;" in content
    assert "gap: 2px;" in content
