import pytest

from palpiteiro.automation.caixa_browser import CaixaBrowser
from palpiteiro.automation.caixa_models import CaixaGame, CaixaTransferState
from palpiteiro.automation.caixa_selectors import mega_sena_number_selector, dupla_sena_number_selector, dia_de_sorte_number_selector, dia_de_sorte_month_selector
from palpiteiro.automation.caixa_validation import (
    CaixaValidationError,
    validate_game,
    validate_games,
    validate_mega_sena_numbers,
    validate_lotofacil_numbers,
    validate_lotomania_numbers,
    validate_mais_milionaria_numbers,
    validate_mais_milionaria_trevos,
    validate_quina_numbers,
    validate_dupla_sena_numbers,
    validate_dia_de_sorte_numbers,
    validate_dia_de_sorte_month,
    validate_super_sete_numbers,
    verify_numbers,
)


def test_caixa_permite_somente_hosts_oficiais_https() -> None:
    assert CaixaBrowser.is_allowed_url(
        "https://www.loteriasonline.caixa.gov.br/silce-web/#/home"
    )
    assert CaixaBrowser.is_allowed_url("https://loteriasonline.caixa.gov.br/")
    assert not CaixaBrowser.is_allowed_url("http://www.loteriasonline.caixa.gov.br/")
    assert not CaixaBrowser.is_allowed_url("https://example.com/")


def test_caixa_game_exige_modalidade_e_conteudo() -> None:
    game = CaixaGame("mega-sena", (4, 11, 23, 37, 45, 58))

    assert game.lottery_slug == "mega-sena"
    assert game.numbers == (4, 11, 23, 37, 45, 58)

    with pytest.raises(ValueError):
        CaixaGame("", (1, 2, 3))
    with pytest.raises(ValueError):
        CaixaGame("mega-sena", ())


def test_estados_basicos_da_transferencia() -> None:
    assert CaixaTransferState.READY.value == "ready"
    assert CaixaTransferState.WAITING_LOGIN.value == "waiting_login"
    assert CaixaTransferState.PREPARED.value == "prepared"


def test_mega_sena_valida_dezenas_e_normaliza_ordem() -> None:
    assert validate_mega_sena_numbers([58, 4, 45, 11, 37, 23]) == (4, 11, 23, 37, 45, 58)


@pytest.mark.parametrize(
    "numbers",
    [
        [1, 2, 3, 4, 5],
        [1, 2, 3, 4, 5, 5],
        [0, 2, 3, 4, 5, 6],
        [1, 2, 3, 4, 5, 61],
        [1, 2, 3, 4, 5, "06"],
    ],
)
def test_mega_sena_rejeita_jogo_invalido(numbers) -> None:
    with pytest.raises(CaixaValidationError):
        validate_mega_sena_numbers(numbers)


def test_lotofacil_valida_dezenas_e_regras() -> None:
    numbers = list(range(25, 10, -1))
    assert validate_lotofacil_numbers(numbers) == tuple(range(11, 26))
    with pytest.raises(CaixaValidationError):
        validate_lotofacil_numbers(list(range(1, 15)))
    with pytest.raises(CaixaValidationError):
        validate_lotofacil_numbers(list(range(1, 21)) + [26])


def test_quina_valida_dezenas_e_regras() -> None:
    assert validate_quina_numbers([80, 5, 42, 17, 3]) == (3, 5, 17, 42, 80)
    with pytest.raises(CaixaValidationError):
        validate_quina_numbers([1, 2, 3, 4])
    with pytest.raises(CaixaValidationError):
        validate_quina_numbers([1, 2, 3, 4, 5, 5])
    with pytest.raises(CaixaValidationError):
        validate_quina_numbers([1, 2, 3, 4, 5, 81])


def test_mais_milionaria_valida_dezenas_e_trevos() -> None:
    assert validate_mais_milionaria_numbers([50, 6, 12, 22, 31, 44]) == (6, 12, 22, 31, 44, 50)
    assert validate_mais_milionaria_trevos([6, 2]) == (2, 6)
    with pytest.raises(CaixaValidationError):
        validate_mais_milionaria_numbers([1, 2, 3, 4, 5])
    with pytest.raises(CaixaValidationError):
        validate_mais_milionaria_trevos([1])


def test_lotomania_exige_50_dezenas_de_00_a_99() -> None:
    values = list(range(50))
    assert validate_lotomania_numbers(values) == tuple(values)
    with pytest.raises(CaixaValidationError):
        validate_lotomania_numbers(list(range(49)))
    with pytest.raises(CaixaValidationError):
        validate_lotomania_numbers(list(range(49)) + [99, 99])
    with pytest.raises(CaixaValidationError):
        validate_lotomania_numbers(list(range(49)) + [100])


def test_dupla_sena_valida_dezenas_e_regras() -> None:
    assert validate_dupla_sena_numbers([50, 6, 12, 22, 31, 44]) == (6, 12, 22, 31, 44, 50)
    with pytest.raises(CaixaValidationError):
        validate_dupla_sena_numbers([1, 2, 3, 4, 5])
    with pytest.raises(CaixaValidationError):
        validate_dupla_sena_numbers([1, 2, 3, 4, 5, 6, 6])
    with pytest.raises(CaixaValidationError):
        validate_dupla_sena_numbers(list(range(1, 16)) + [51])


def test_validacao_de_jogo_restringe_modalidade_nao_adaptada() -> None:
    validated = validate_game(CaixaGame("mega-sena", (58, 4, 45, 11, 37, 23)))

    assert validated.numbers == (4, 11, 23, 37, 45, 58)
    with pytest.raises(CaixaValidationError):
        validate_game(CaixaGame("dia-de-sorte", (1, 2, 3, 4, 5, 6, 7)))


def test_verify_numbers_exige_conjunto_exato() -> None:
    verify_numbers((4, 11, 23, 37, 45, 58), [58, 4, 45, 11, 37, 23])

    with pytest.raises(CaixaValidationError, match="Detectado"):
        verify_numbers((4, 11, 23, 37, 45, 58), [4, 11, 23, 37, 45])


def test_seletor_da_dezena_mega_sena_e_centralizado() -> None:
    assert mega_sena_number_selector(1) == "a#n01"
    assert mega_sena_number_selector(60) == "a#n60"
    with pytest.raises(ValueError):
        mega_sena_number_selector(61)


def test_seletor_da_dezena_dupla_sena() -> None:
    assert dupla_sena_number_selector(1) == "a#n01"
    assert dupla_sena_number_selector(50) == "a#n50"
    with pytest.raises(ValueError):
        dupla_sena_number_selector(51)


def test_dia_de_sorte_valida_dezenas_e_mes() -> None:
    assert validate_dia_de_sorte_numbers([31, 1, 7, 12, 18, 22, 25]) == (1, 7, 12, 18, 22, 25, 31)
    assert validate_dia_de_sorte_month("janeiro") == "Janeiro"
    with pytest.raises(CaixaValidationError):
        validate_dia_de_sorte_numbers([1, 2, 3, 4, 5, 6])
    with pytest.raises(CaixaValidationError):
        validate_dia_de_sorte_month("mês inválido")


def test_seletor_dia_de_sorte() -> None:
    assert dia_de_sorte_number_selector(31) == "a#n31"
    assert "Janeiro" in dia_de_sorte_month_selector("Janeiro")


def test_super_sete_valida_opcoes_por_coluna() -> None:
    values = tuple(column * 10 + 1 for column in range(7))
    assert validate_super_sete_numbers(values) == values
    with pytest.raises(CaixaValidationError):
        validate_super_sete_numbers((1, 2, 3, 4, 5, 6))


def test_validate_games_valida_todos_antes_da_transferencia() -> None:
    games = validate_games(
        [
            CaixaGame("mega-sena", (4, 11, 23, 37, 45, 58)),
            CaixaGame("mega-sena", (2, 17, 21, 33, 49, 60)),
        ]
    )

    assert len(games) == 2
    assert games[0].numbers == (4, 11, 23, 37, 45, 58)

    with pytest.raises(CaixaValidationError):
        validate_games([CaixaGame("mega-sena", (1, 2, 3, 4, 5))])
    with pytest.raises(CaixaValidationError):
        validate_games([])
