"""Integração assistida e opcional com o portal oficial das Loterias CAIXA."""

from palpiteiro.automation.caixa_models import CaixaGame, CaixaTransferState
from palpiteiro.automation.caixa_validation import (
    CaixaValidationError,
    validate_game,
    validate_games,
    validate_mega_sena_numbers,
    validate_lotofacil_numbers,
    validate_quina_numbers,
    validate_mais_milionaria_numbers,
    validate_mais_milionaria_trevos,
    validate_lotomania_numbers,
    validate_dupla_sena_numbers,
    validate_dia_de_sorte_numbers,
    validate_dia_de_sorte_month,
    validate_super_sete_numbers,
    verify_numbers,
)

__all__ = [
    "CaixaGame",
    "CaixaTransferState",
    "CaixaValidationError",
    "validate_game",
    "validate_games",
    "validate_mega_sena_numbers",
    "validate_lotofacil_numbers",
    "validate_quina_numbers",
    "validate_mais_milionaria_numbers",
    "validate_mais_milionaria_trevos",
    "validate_lotomania_numbers",
    "validate_dupla_sena_numbers",
    "validate_dia_de_sorte_numbers",
    "validate_dia_de_sorte_month",
    "validate_super_sete_numbers",
    "verify_numbers",
]
