class CaixaAutomationError(RuntimeError):
    """Erro base da automação assistida das Loterias CAIXA."""


class CaixaNavigationError(CaixaAutomationError):
    """O portal não pôde ser aberto ou saiu do domínio autorizado."""


class CaixaSelectorError(CaixaAutomationError):
    """Um elemento esperado não foi localizado no portal."""


class CaixaVerificationError(CaixaAutomationError):
    """Os números detectados no portal não correspondem ao jogo esperado."""
