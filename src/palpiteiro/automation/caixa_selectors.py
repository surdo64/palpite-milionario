"""Constantes de navegação; seletores de modalidades serão adicionados após validação visual."""

CAIXA_PORTAL_URL = "https://www.loteriasonline.caixa.gov.br/silce-web/#/home"
CAIXA_MEGA_SENA_URL = "https://www.loteriasonline.caixa.gov.br/silce-web/#/mega-sena"
CAIXA_ALLOWED_HOSTS = frozenset({"www.loteriasonline.caixa.gov.br", "loteriasonline.caixa.gov.br"})


def mega_sena_number_selector(number: int) -> str:
    if number < 1 or number > 60:
        raise ValueError("A dezena da Mega-Sena deve estar entre 01 e 60.")
    return f"a#n{number:02d}"


def lotofacil_number_selector(number: int) -> str:
    if number < 1 or number > 25:
        raise ValueError("A dezena da Lotofácil deve estar entre 01 e 25.")
    return f"a#n{number:02d}"


def quina_number_selector(number: int) -> str:
    if number < 1 or number > 80:
        raise ValueError("A dezena da Quina deve estar entre 01 e 80.")
    return f"a#n{number:02d}"


def mais_milionaria_number_selector(number: int) -> str:
    if number < 1 or number > 50:
        raise ValueError("A dezena da +Milionária deve estar entre 01 e 50.")
    return f"a#n{number:02d}"


def mais_milionaria_trevo_selector(number: int) -> str:
    if number < 1 or number > 6:
        raise ValueError("O trevo da +Milionária deve estar entre 1 e 6.")
    return f"#trevo{number}"


def lotomania_number_selector(number: int) -> str:
    if number < 0 or number > 99:
        raise ValueError("A dezena da Lotomania deve estar entre 00 e 99.")
    return f"a#n{number:02d}"


def dupla_sena_number_selector(number: int) -> str:
    if number < 1 or number > 50:
        raise ValueError("A dezena da Dupla Sena deve estar entre 01 e 50.")
    return f"a#n{number:02d}"


def dia_de_sorte_number_selector(number: int) -> str:
    if number < 1 or number > 31:
        raise ValueError("A dezena do Dia de Sorte deve estar entre 01 e 31.")
    return f"a#n{number:02d}"


def dia_de_sorte_month_selector(month: str) -> str:
    if not isinstance(month, str) or not month.strip():
        raise ValueError("O mês da sorte deve ser informado.")
    return f"li[ng-click*='configurarMes']:has-text('{month.strip()}')"


def super_sete_number_selector(number: int) -> str:
    if number < 1 or number > 70:
        raise ValueError("A opção do Super Sete deve estar entre 01 e 70.")
    return f"a#n{number}"
