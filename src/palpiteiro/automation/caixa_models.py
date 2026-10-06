from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CaixaTransferState(Enum):
    READY = "ready"
    WAITING_LOGIN = "waiting_login"
    TRANSFERRING = "transferring"
    PREPARED = "prepared"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass(frozen=True)
class CaixaGame:
    """Jogo estruturado para transferência, sem dados de autenticação ou pagamento."""

    lottery_slug: str
    numbers: tuple[int, ...]
    special: tuple[object, ...] = ()

    def __post_init__(self) -> None:
        if not self.lottery_slug.strip():
            raise ValueError("A modalidade do jogo é obrigatória.")
        if not self.numbers and not self.special:
            raise ValueError("O jogo precisa conter números ou elementos especiais.")
