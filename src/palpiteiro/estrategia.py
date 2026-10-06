from __future__ import annotations

from itertools import combinations
from random import Random

from palpiteiro.historico import StatisticsStore
from palpiteiro.loterias import LOTTERIES, LotteryConfig


BET_PROFILES = {
    "conservador": "Favorece numeros mais frequentes e reduz repeticao do ultimo concurso.",
    "equilibrado": "Mistura frequencia historica com distribuicao mais balanceada.",
    "agressivo": "Aceita mais variacao e da mais espaço para numeros menos obvios.",
    "fechamento": "Monta jogos em lote buscando melhor cobertura de combinacoes dentro de um grupo base.",
}


def _weighted_sample_without_replacement(
    options: list[object],
    weights: dict[str, float],
    amount: int,
    rng: Random,
) -> tuple[object, ...]:
    selected: list[object] = []
    available = list(options)

    for _ in range(amount):
        total_weight = sum(weights[str(option)] for option in available)
        threshold = rng.random() * total_weight
        current = 0.0
        chosen = available[-1]

        for option in available:
            current += weights[str(option)]
            if current >= threshold:
                chosen = option
                break

        selected.append(chosen)
        available.remove(chosen)

    return tuple(selected)


def _recent_numbers(history: list[dict[str, object]], amount: int = 1) -> set[int]:
    numbers: set[int] = set()
    for item in reversed(history[-amount:]):
        values = item.get("numbers", ())
        if isinstance(values, (tuple, list)):
            numbers.update(int(value) for value in values)
    return numbers


def _longest_sequence(numbers: list[int]) -> int:
    if not numbers:
        return 0
    longest = 1
    current = 1
    for previous, current_value in zip(numbers, numbers[1:]):
        if current_value == previous + 1:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return longest


def _parity_count(numbers: list[int]) -> int:
    return sum(1 for value in numbers if value % 2 == 0)


def _profile_weight(
    profile: str,
    number: int,
    base_weight: float,
    recent_draw: set[int],
) -> float:
    adjusted = base_weight
    if profile == "conservador":
        adjusted *= 1.35
        if number in recent_draw:
            adjusted *= 0.55
    elif profile == "equilibrado":
        if number in recent_draw:
            adjusted *= 0.75
    elif profile == "fechamento":
        adjusted *= 1.15
        if number in recent_draw:
            adjusted *= 0.7
    elif profile == "agressivo":
        adjusted = max(1.0, (100.0 / adjusted) * 5.0)
        if number in recent_draw:
            adjusted *= 1.1
    return max(adjusted, 0.1)


def _build_profiled_number_weights(
    config: LotteryConfig,
    statistics: dict[str, object],
    profile: str,
    history: list[dict[str, object]],
) -> dict[str, float]:
    number_weights = statistics["numbers"]
    assert isinstance(number_weights, dict)
    recent_draw = _recent_numbers(history, 1)
    adjusted: dict[str, float] = {}
    for number in range(config.min_value, config.max_value + 1):
        base_weight = float(number_weights[str(number)])
        adjusted[str(number)] = _profile_weight(profile, number, base_weight, recent_draw)
    return adjusted


def _is_candidate_valid(profile: str, numbers: list[int], selected_picks: int) -> bool:
    if profile == "agressivo":
        return True

    even_count = _parity_count(numbers)
    odd_count = selected_picks - even_count
    if profile == "conservador":
        if abs(even_count - odd_count) > 2:
            return False
        if _longest_sequence(numbers) > 2:
            return False
    elif profile == "equilibrado":
        if abs(even_count - odd_count) > 3:
            return False
        if _longest_sequence(numbers) > 3:
            return False
    elif profile == "fechamento":
        if abs(even_count - odd_count) > 3:
            return False
        if _longest_sequence(numbers) > 3:
            return False
    return True


def _generate_standard_profiled_bet(
    config: LotteryConfig,
    statistics: dict[str, object],
    history: list[dict[str, object]],
    profile: str,
    rng: Random,
    selected_picks: int,
) -> tuple[int, ...]:
    weights = _build_profiled_number_weights(config, statistics, profile, history)
    options = list(range(config.min_value, config.max_value + 1))
    for _ in range(200):
        chosen = _weighted_sample_without_replacement(options, weights, selected_picks, rng)
        numbers = sorted(int(number) for number in chosen)
        if _is_candidate_valid(profile, numbers, selected_picks):
            return tuple(numbers)
    return tuple(sorted(int(number) for number in _weighted_sample_without_replacement(options, weights, selected_picks, rng)))


def _combination_pairs(numbers: tuple[int, ...]) -> set[tuple[int, int]]:
    return {tuple(pair) for pair in combinations(numbers, 2)}


def _build_closure_pool(
    config: LotteryConfig,
    statistics: dict[str, object],
    history: list[dict[str, object]],
    rng: Random,
    selected_picks: int,
    quantity: int,
) -> tuple[int, ...]:
    weights = _build_profiled_number_weights(config, statistics, "fechamento", history)
    options = list(range(config.min_value, config.max_value + 1))
    pool_size = min(
        len(options),
        max(selected_picks + 3, min(selected_picks + quantity + 1, selected_picks + 8)),
    )
    for _ in range(100):
        chosen = _weighted_sample_without_replacement(options, weights, pool_size, rng)
        numbers = tuple(sorted(int(number) for number in chosen))
        even_count = _parity_count(list(numbers))
        if abs(even_count - (pool_size - even_count)) <= max(3, pool_size // 3):
            return numbers
    return tuple(sorted(int(number) for number in _weighted_sample_without_replacement(options, weights, pool_size, rng)))


def _score_closure_candidate(
    candidate: tuple[int, ...],
    covered_pairs: set[tuple[int, int]],
    weights: dict[str, float],
) -> tuple[float, float]:
    candidate_pairs = _combination_pairs(candidate)
    new_pairs = len(candidate_pairs - covered_pairs)
    weight_score = sum(weights[str(number)] for number in candidate)
    return float(new_pairs), weight_score


def _generate_closure_bets(
    config: LotteryConfig,
    statistics: dict[str, object],
    history: list[dict[str, object]],
    rng: Random,
    quantity: int,
    selected_picks: int,
    special_picks: int | None,
    digits_per_column: int | None,
) -> list[dict[str, object]]:
    if config.columns:
        return [
            _generate_from_statistics(
                config,
                statistics,
                history,
                "equilibrado",
                rng,
                selected_picks,
                special_picks,
                digits_per_column,
            )
            for _ in range(quantity)
        ]

    pool = _build_closure_pool(config, statistics, history, rng, selected_picks, quantity)
    weights = _build_profiled_number_weights(config, statistics, "fechamento", history)
    covered_pairs: set[tuple[int, int]] = set()
    chosen_keys: set[tuple[int, ...]] = set()
    bets: list[dict[str, object]] = []

    for _ in range(quantity):
        best_candidate: tuple[int, ...] | None = None
        best_score = (-1.0, -1.0)

        if len(pool) == selected_picks:
            candidates = [pool]
        else:
            candidates = [
                tuple(sorted(rng.sample(pool, selected_picks)))
                for _ in range(1200)
            ]

        for candidate in candidates:
            sorted_candidate = candidate
            if sorted_candidate in chosen_keys:
                continue
            if not _is_candidate_valid("fechamento", list(sorted_candidate), selected_picks):
                continue
            score = _score_closure_candidate(sorted_candidate, covered_pairs, weights)
            if score > best_score:
                best_candidate = sorted_candidate
                best_score = score

        if best_candidate is None:
            best_candidate = _generate_standard_profiled_bet(
                config,
                statistics,
                history,
                "fechamento",
                rng,
                selected_picks,
            )

        chosen_keys.add(best_candidate)
        covered_pairs.update(_combination_pairs(best_candidate))
        bet: dict[str, object] = {"numbers": best_candidate}

        special_weights = statistics.get("special")
        if isinstance(special_weights, dict):
            selected_special_picks = special_picks if special_picks is not None else config.special_picks
            if config.special_values:
                chosen_special = _weighted_sample_without_replacement(
                    list(config.special_values),
                    special_weights,
                    selected_special_picks,
                    rng,
                )
                bet["special"] = tuple(chosen_special)
            elif config.special_min is not None and config.special_max is not None:
                chosen_special = _weighted_sample_without_replacement(
                    list(range(config.special_min, config.special_max + 1)),
                    special_weights,
                    selected_special_picks,
                    rng,
                )
                bet["special"] = tuple(sorted(int(value) for value in chosen_special))

        bets.append(bet)

    return bets


def _generate_from_statistics(
    config: LotteryConfig,
    statistics: dict[str, object],
    history: list[dict[str, object]],
    profile: str,
    rng: Random | None = None,
    picks: int | None = None,
    special_picks: int | None = None,
    digits_per_column: int | None = None,
) -> dict[str, object]:
    randomizer = rng or Random()
    selected_picks = picks if picks is not None else config.picks
    selected_special_picks = special_picks if special_picks is not None else config.special_picks
    selected_digits_per_column = (
        digits_per_column if digits_per_column is not None else config.digits_per_column
    )

    if config.columns:
        column_weights = statistics["columns"]
        assert isinstance(column_weights, list)
        columns = []
        for weights in column_weights:
            assert isinstance(weights, dict)
            digits = _weighted_sample_without_replacement(
                list(range(10)),
                weights,
                selected_digits_per_column,
                randomizer,
            )
            columns.append(tuple(sorted(int(value) for value in digits)))
        return {"columns": tuple(columns)}

    numbers = _generate_standard_profiled_bet(
        config,
        statistics,
        history,
        profile,
        randomizer,
        selected_picks,
    )
    bet: dict[str, object] = {"numbers": numbers}

    special_weights = statistics.get("special")
    if not isinstance(special_weights, dict):
        return bet

    if config.special_values:
        chosen = _weighted_sample_without_replacement(
            list(config.special_values),
            special_weights,
            selected_special_picks,
            randomizer,
        )
        bet["special"] = tuple(chosen)
        return bet

    if config.special_min is not None and config.special_max is not None:
        chosen = _weighted_sample_without_replacement(
            list(range(config.special_min, config.special_max + 1)),
            special_weights,
            selected_special_picks,
            randomizer,
        )
        bet["special"] = tuple(sorted(int(value) for value in chosen))

    return bet


def generate_bet(
    slug: str,
    store: StatisticsStore | None = None,
    rng: Random | None = None,
    picks: int | None = None,
    special_picks: int | None = None,
    digits_per_column: int | None = None,
    profile: str = "equilibrado",
) -> dict[str, object]:
    config = LOTTERIES[slug]
    statistics_store = store or StatisticsStore()
    statistics_entry = statistics_store.get_statistics(slug)

    if statistics_entry is None:
        return config.generate_random(rng, picks, special_picks, digits_per_column)

    statistics = statistics_entry.get("estatisticas")
    if not isinstance(statistics, dict):
        return config.generate_random(rng, picks, special_picks, digits_per_column)

    history = statistics_entry.get("historico")
    if not isinstance(history, list):
        history = []

    selected_profile = profile if profile in BET_PROFILES else "equilibrado"
    return _generate_from_statistics(
        config,
        statistics,
        history,
        selected_profile,
        rng,
        picks,
        special_picks,
        digits_per_column,
    )


def generate_bets(
    slug: str,
    quantity: int,
    store: StatisticsStore | None = None,
    rng: Random | None = None,
    picks: int | None = None,
    special_picks: int | None = None,
    digits_per_column: int | None = None,
    profile: str = "equilibrado",
) -> list[dict[str, object]]:
    if quantity < 1:
        return []

    config = LOTTERIES[slug]
    statistics_store = store or StatisticsStore()
    statistics_entry = statistics_store.get_statistics(slug)
    selected_profile = profile if profile in BET_PROFILES else "equilibrado"
    randomizer = rng or Random()

    if selected_profile != "fechamento" or statistics_entry is None:
        return [
            generate_bet(
                slug,
                statistics_store,
                randomizer,
                picks,
                special_picks,
                digits_per_column,
                selected_profile,
            )
            for _ in range(quantity)
        ]

    statistics = statistics_entry.get("estatisticas")
    history = statistics_entry.get("historico")
    if not isinstance(statistics, dict) or not isinstance(history, list):
        return [
            generate_bet(
                slug,
                statistics_store,
                randomizer,
                picks,
                special_picks,
                digits_per_column,
                selected_profile,
            )
            for _ in range(quantity)
        ]

    selected_picks = picks if picks is not None else config.picks
    return _generate_closure_bets(
        config,
        statistics,
        history,
        randomizer,
        quantity,
        selected_picks,
        special_picks,
        digits_per_column,
    )
