from __future__ import annotations

import argparse
from typing import Sequence

from palpiteiro import __version__
from palpiteiro.estrategia import BET_PROFILES, generate_bets
from palpiteiro.historico import StatisticsStore, format_currency
from palpiteiro.loterias import LOTTERIES, format_brl_from_cents, get_lottery


MENU_ORDER = [
    "mega-sena",
    "lotofacil",
    "quina",
    "mais-milionaria",
    "lotomania",
    "dupla-sena",
    "dia-de-sorte",
    "supersete",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="palpite-milionario",
        description="Gera palpites para loterias brasileiras.",
    )
    parser.add_argument("loteria", nargs="?", help="Nome da loteria.")
    parser.add_argument(
        "-n",
        "--quantidade",
        type=int,
        default=1,
        help="Quantidade de palpites a gerar.",
    )
    parser.add_argument(
        "--listar",
        action="store_true",
        help="Lista as loterias suportadas.",
    )
    parser.add_argument(
        "--versao",
        action="store_true",
        help="Mostra a versao do programa.",
    )
    parser.add_argument(
        "--perfil",
        choices=sorted(BET_PROFILES),
        default="equilibrado",
        help="Perfil estatistico para gerar os palpites.",
    )
    return parser


def render_horizontal_menu() -> None:
    print(f"Palpite Milionário | versao {__version__}")
    print("Escolha uma loteria:")
    parts = []
    for index, key in enumerate(MENU_ORDER, start=1):
        config = LOTTERIES[key]
        parts.append(f"[{index}] {config.display_name}")
    print(" | ".join(parts))


def prompt_interactive_selection() -> tuple[str, int]:
    render_horizontal_menu()

    selection = input("Numero da loteria: ").strip()
    try:
        selected_index = int(selection)
    except ValueError as error:
        raise ValueError("Selecione um numero valido do menu.") from error

    if selected_index < 1 or selected_index > len(MENU_ORDER):
        raise ValueError("Selecione um numero valido do menu.")

    quantity_raw = input("Quantidade de jogos [1]: ").strip()
    quantity = 1 if quantity_raw == "" else int(quantity_raw)
    if quantity < 1:
        raise ValueError("A quantidade deve ser maior que zero.")

    return MENU_ORDER[selected_index - 1], quantity


def print_bets(lottery_name: str, quantity: int, profile: str = "equilibrado") -> None:
    lottery = get_lottery(lottery_name)
    store = StatisticsStore()
    sync_result = store.refresh_all()
    price_per_game = lottery.bet_price_cents()
    total_price = price_per_game * quantity
    print(f"{lottery.display_name} | versao {__version__}")
    print(sync_result.message)
    statistics = store.get_statistics(lottery.slug)
    if statistics:
        prize = format_currency(statistics.get("proximo_premio"))
        next_date = statistics.get("data_proximo_concurso") or "sem data"
        next_contest = statistics.get("concurso_proximo") or "?"
        print(f"Proximo premio estimado: {prize} | Proximo concurso: {next_contest} em {next_date}")
    print(f"Perfil estatistico: {profile}")
    print(f"Preco por jogo: {format_brl_from_cents(price_per_game)} | Total: {format_brl_from_cents(total_price)}")
    bets = generate_bets(lottery.slug, quantity, store, profile=profile)
    for index, bet in enumerate(bets, start=1):
        print(f"Jogo {index}: {lottery.format_bet(bet)}")


def run_cli(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.versao:
        print(__version__)
        return 0

    if args.listar:
        print("Loterias suportadas:")
        for config in LOTTERIES.values():
            print(f"- {config.display_name} ({config.slug})")
        return 0

    if not args.loteria:
        try:
            lottery_name, quantity = prompt_interactive_selection()
        except ValueError as error:
            parser.error(str(error))
        print_bets(lottery_name, quantity, args.perfil)
        return 0

    if args.quantidade < 1:
        parser.error("a quantidade deve ser maior que zero")

    print_bets(args.loteria, args.quantidade, args.perfil)
    return 0
