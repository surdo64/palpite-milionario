from __future__ import annotations

from collections.abc import Iterable

from palpiteiro.automation.caixa_exceptions import CaixaAutomationError
from palpiteiro.automation.caixa_models import CaixaGame
from palpiteiro.loterias import get_lottery
from palpiteiro.loterias import MONTHS


class CaixaValidationError(CaixaAutomationError, ValueError):
    """Jogo incompatível com as regras da modalidade selecionada."""


def validate_mega_sena_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    """Valida dezenas da Mega-Sena antes de qualquer interação com o portal."""
    values = tuple(numbers)
    lottery = get_lottery("mega-sena")

    if not values:
        raise CaixaValidationError("A Mega-Sena precisa de pelo menos seis dezenas.")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas da Mega-Sena devem ser números inteiros.")
    if len(values) < lottery.min_picks or len(values) > lottery.max_picks:
        raise CaixaValidationError(
            f"A Mega-Sena aceita de {lottery.min_picks} a {lottery.max_picks} dezenas."
        )
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da Mega-Sena não pode conter dezenas duplicadas.")
    if any(value < lottery.min_value or value > lottery.max_value for value in values):
        raise CaixaValidationError(
            f"As dezenas da Mega-Sena devem estar entre {lottery.min_value:02d} e {lottery.max_value:02d}."
        )

    return tuple(sorted(values))


def validate_lotofacil_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    """Valida dezenas da Lotofácil antes de qualquer interação com o portal."""
    values = tuple(numbers)
    lottery = get_lottery("lotofacil")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas da Lotofácil devem ser números inteiros.")
    if len(values) < lottery.min_picks or len(values) > lottery.max_picks:
        raise CaixaValidationError(
            f"A Lotofácil aceita de {lottery.min_picks} a {lottery.max_picks} dezenas."
        )
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da Lotofácil não pode conter dezenas duplicadas.")
    if any(value < lottery.min_value or value > lottery.max_value for value in values):
        raise CaixaValidationError("As dezenas da Lotofácil devem estar entre 01 e 25.")
    return tuple(sorted(values))


def validate_quina_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    """Valida dezenas da Quina antes de qualquer interação com o portal."""
    values = tuple(numbers)
    lottery = get_lottery("quina")
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas da Quina devem ser números inteiros.")
    if len(values) < lottery.min_picks or len(values) > lottery.max_picks:
        raise CaixaValidationError(f"A Quina aceita de {lottery.min_picks} a {lottery.max_picks} dezenas.")
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da Quina não pode conter dezenas duplicadas.")
    if any(value < lottery.min_value or value > lottery.max_value for value in values):
        raise CaixaValidationError("As dezenas da Quina devem estar entre 01 e 80.")
    return tuple(sorted(values))


def validate_mais_milionaria_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    values = tuple(numbers)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas da +Milionária devem ser números inteiros.")
    if len(values) < 6 or len(values) > 12:
        raise CaixaValidationError("A +Milionária aceita de 6 a 12 dezenas.")
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da +Milionária não pode conter dezenas duplicadas.")
    if any(value < 1 or value > 50 for value in values):
        raise CaixaValidationError("As dezenas da +Milionária devem estar entre 01 e 50.")
    return tuple(sorted(values))


def validate_mais_milionaria_trevos(trevos: Iterable[object]) -> tuple[int, ...]:
    values = tuple(trevos)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("Os trevos da +Milionária devem ser números inteiros.")
    if len(values) < 2 or len(values) > 6:
        raise CaixaValidationError("A +Milionária aceita de 2 a 6 trevos.")
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da +Milionária não pode conter trevos duplicados.")
    if any(value < 1 or value > 6 for value in values):
        raise CaixaValidationError("Os trevos da +Milionária devem estar entre 1 e 6.")
    return tuple(sorted(values))


def validate_lotomania_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    values = tuple(numbers)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas da Lotomania devem ser números inteiros.")
    if len(values) != 50:
        raise CaixaValidationError("A Lotomania exige exatamente 50 dezenas.")
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da Lotomania não pode conter dezenas duplicadas.")
    if any(value < 0 or value > 99 for value in values):
        raise CaixaValidationError("As dezenas da Lotomania devem estar entre 00 e 99.")
    return tuple(sorted(values))


def validate_dupla_sena_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    values = tuple(numbers)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas da Dupla Sena devem ser números inteiros.")
    if len(values) < 6 or len(values) > 15:
        raise CaixaValidationError("A Dupla Sena aceita de 6 a 15 dezenas.")
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo da Dupla Sena não pode conter dezenas duplicadas.")
    if any(value < 1 or value > 50 for value in values):
        raise CaixaValidationError("As dezenas da Dupla Sena devem estar entre 01 e 50.")
    return tuple(sorted(values))


def validate_dia_de_sorte_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    values = tuple(numbers)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As dezenas do Dia de Sorte devem ser números inteiros.")
    if len(values) < 7 or len(values) > 15:
        raise CaixaValidationError("O Dia de Sorte aceita de 7 a 15 dezenas.")
    if len(set(values)) != len(values):
        raise CaixaValidationError("O jogo do Dia de Sorte não pode conter dezenas duplicadas.")
    if any(value < 1 or value > 31 for value in values):
        raise CaixaValidationError("As dezenas do Dia de Sorte devem estar entre 01 e 31.")
    return tuple(sorted(values))


def validate_dia_de_sorte_month(month: object) -> str:
    if not isinstance(month, str) or month.strip().casefold() not in {item.casefold() for item in MONTHS}:
        raise CaixaValidationError("Informe um mês da sorte válido para o Dia de Sorte.")
    return next(item for item in MONTHS if item.casefold() == month.strip().casefold())


def validate_super_sete_numbers(numbers: Iterable[object]) -> tuple[int, ...]:
    values = tuple(numbers)
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        raise CaixaValidationError("As opções do Super Sete devem ser números inteiros.")
    if len(values) < 7 or len(values) > 21 or len(set(values)) != len(values):
        raise CaixaValidationError("O Super Sete aceita de 7 a 21 opções sem duplicidade.")
    if any(value < 1 or value > 70 for value in values):
        raise CaixaValidationError("As opções do Super Sete devem estar entre 01 e 70.")
    counts = [sum(1 for value in values if (value - 1) // 10 == column) for column in range(7)]
    if any(count < 1 or count > 3 for count in counts):
        raise CaixaValidationError("O Super Sete exige de 1 a 3 opções por coluna.")
    return tuple(sorted(values))


def validate_game(game: CaixaGame) -> CaixaGame:
    """Valida um jogo transferível; nesta etapa, somente Mega-Sena é suportada."""
    validators = {
        "mega-sena": validate_mega_sena_numbers,
        "lotofacil": validate_lotofacil_numbers,
        "quina": validate_quina_numbers,
        "mais-milionaria": validate_mais_milionaria_numbers,
        "lotomania": validate_lotomania_numbers,
        "dupla-sena": validate_dupla_sena_numbers,
        "dia-de-sorte": validate_dia_de_sorte_numbers,
        "supersete": validate_super_sete_numbers,
    }
    validator = validators.get(game.lottery_slug)
    if validator is None:
        raise CaixaValidationError(
            "A transferência assistida está disponível somente para Mega-Sena, Lotofácil, Quina, +Milionária, Lotomania e Dupla Sena."
        )
    if game.lottery_slug == "mais-milionaria":
        special = validate_mais_milionaria_trevos(game.special)
    elif game.lottery_slug == "dia-de-sorte":
        if len(game.special) != 1:
            raise CaixaValidationError("O Dia de Sorte exige um único mês da sorte.")
        special = (validate_dia_de_sorte_month(game.special[0]),)
    else:
        special = game.special
    return CaixaGame(game.lottery_slug, validator(game.numbers), special)


def verify_numbers(expected: Iterable[object], selected: Iterable[object]) -> None:
    """Confirma que o volante marcou exatamente as dezenas esperadas."""
    expected_values = set(expected)
    selected_values = set(selected)
    if expected_values != selected_values:
        expected_rendered = " ".join(f"{value:02d}" for value in sorted(expected_values))
        selected_rendered = " ".join(
            f"{value:02d}" for value in sorted(value for value in selected_values if isinstance(value, int))
        ) or "nenhuma"
        raise CaixaValidationError(
            "Os números selecionados no portal não correspondem ao jogo esperado. "
            f"Esperado: {expected_rendered}. Detectado: {selected_rendered}."
        )


def validate_games(games: Iterable[CaixaGame]) -> tuple[CaixaGame, ...]:
    """Valida antecipadamente todos os jogos antes de iniciar uma transferência."""
    validated = tuple(validate_game(game) for game in games)
    if not validated:
        raise CaixaValidationError("Selecione pelo menos um jogo para transferir.")
    return validated
