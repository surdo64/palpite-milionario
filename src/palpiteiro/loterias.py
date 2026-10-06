from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Sequence


MONTHS = (
    "Janeiro",
    "Fevereiro",
    "Marco",
    "Abril",
    "Maio",
    "Junho",
    "Julho",
    "Agosto",
    "Setembro",
    "Outubro",
    "Novembro",
    "Dezembro",
)


@dataclass(frozen=True)
class LotteryConfig:
    slug: str
    display_name: str
    api_modalidade: str
    api_path: str
    min_value: int
    max_value: int
    picks: int
    min_picks: int
    max_picks: int
    zero_padded_width: int
    special_label: str | None = None
    special_min: int | None = None
    special_max: int | None = None
    special_picks: int = 0
    min_special_picks: int = 0
    max_special_picks: int = 0
    special_width: int = 0
    special_values: Sequence[str] | None = None
    columns: int = 0
    digits_per_column: int = 0
    min_digits_per_column: int = 0
    max_digits_per_column: int = 0
    price_table: dict[object, int] | None = None

    def generate_random(
        self,
        rng: Random | None = None,
        picks: int | None = None,
        special_picks: int | None = None,
        digits_per_column: int | None = None,
    ) -> dict[str, object]:
        randomizer = rng or Random()
        selected_picks = picks or self.picks
        selected_special_picks = special_picks if special_picks is not None else self.special_picks
        selected_digits_per_column = (
            digits_per_column if digits_per_column is not None else self.digits_per_column
        )

        if self.columns:
            columns = []
            for _ in range(self.columns):
                digits = sorted(randomizer.sample(range(10), selected_digits_per_column))
                columns.append(tuple(digits))
            return {"columns": tuple(columns)}

        numbers = tuple(
            sorted(randomizer.sample(range(self.min_value, self.max_value + 1), selected_picks))
        )
        bet: dict[str, object] = {"numbers": numbers}

        if self.special_values:
            values = tuple(
                sorted(
                    randomizer.sample(
                        tuple(self.special_values),
                        selected_special_picks,
                    )
                )
            )
            bet["special"] = values
        elif self.special_label and self.special_min is not None and self.special_max is not None:
            values = tuple(
                sorted(
                    randomizer.sample(
                        range(self.special_min, self.special_max + 1),
                        selected_special_picks,
                    )
                )
            )
            bet["special"] = values

        return bet

    def generate(
        self,
        rng: Random | None = None,
        picks: int | None = None,
        special_picks: int | None = None,
        digits_per_column: int | None = None,
    ) -> dict[str, object]:
        return self.generate_random(rng, picks, special_picks, digits_per_column)

    def format_bet(self, bet: dict[str, object]) -> str:
        if "columns" in bet:
            columns = bet["columns"]
            assert isinstance(columns, (tuple, list))
            parts = []
            for index, digits in enumerate(columns, start=1):
                assert isinstance(digits, (tuple, list))
                rendered = " ".join(str(digit) for digit in digits)
                parts.append(f"Coluna {index}: {rendered}")
            return " | ".join(parts)

        numbers = bet["numbers"]
        assert isinstance(numbers, (tuple, list))
        rendered_numbers = " ".join(f"{number:0{self.zero_padded_width}d}" for number in numbers)

        if "special" not in bet:
            return rendered_numbers

        special = bet["special"]
        assert isinstance(special, (tuple, list))
        if self.special_values:
            rendered_special = ", ".join(str(value) for value in special)
        else:
            rendered_special = " ".join(
                f"{value:0{self.special_width}d}" for value in special if isinstance(value, int)
            )
        return f"{rendered_numbers} | {self.special_label}: {rendered_special}"

    def bet_price_cents(
        self,
        picks: int | None = None,
        special_picks: int | None = None,
        digits_per_column: int | None = None,
    ) -> int:
        if self.price_table is None:
            raise ValueError(f"Tabela de preco nao configurada para {self.display_name}.")

        if self.slug == "mais-milionaria":
            selected_picks = picks if picks is not None else self.picks
            selected_special_picks = special_picks if special_picks is not None else self.special_picks
            key = (selected_picks, selected_special_picks)
        elif self.slug == "supersete":
            selected_digits_per_column = (
                digits_per_column if digits_per_column is not None else self.digits_per_column
            )
            key = self.columns * selected_digits_per_column
        else:
            key = picks if picks is not None else self.picks

        try:
            return self.price_table[key]
        except KeyError as error:
            raise ValueError(
                f"Nao ha preco oficial configurado para a combinacao selecionada em {self.display_name}."
            ) from error


def format_brl_from_cents(value: int) -> str:
    amount = value / 100
    rendered = f"{amount:,.2f}"
    rendered = rendered.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R${rendered}"


LOTTERIES: dict[str, LotteryConfig] = {
    "mega-sena": LotteryConfig(
        slug="mega-sena",
        display_name="Mega-Sena",
        api_modalidade="Mega-Sena",
        api_path="megasena",
        min_value=1,
        max_value=60,
        picks=6,
        min_picks=6,
        max_picks=20,
        zero_padded_width=2,
        price_table={
            6: 600,
            7: 4200,
            8: 16800,
            9: 50400,
            10: 126000,
            11: 277200,
            12: 554400,
            13: 1029600,
            14: 1801800,
            15: 3003000,
            16: 4804800,
            17: 7425600,
            18: 11138400,
            19: 16279200,
            20: 23256000,
        },
    ),
    "lotofacil": LotteryConfig(
        slug="lotofacil",
        display_name="Lotofacil",
        api_modalidade="Lotofácil",
        api_path="lotofacil",
        min_value=1,
        max_value=25,
        picks=15,
        min_picks=15,
        max_picks=20,
        zero_padded_width=2,
        price_table={
            15: 350,
            16: 5600,
            17: 47600,
            18: 285600,
            19: 1356600,
            20: 5426400,
        },
    ),
    "quina": LotteryConfig(
        slug="quina",
        display_name="Quina",
        api_modalidade="Quina",
        api_path="quina",
        min_value=1,
        max_value=80,
        picks=5,
        min_picks=5,
        max_picks=15,
        zero_padded_width=2,
        price_table={
            5: 300,
            6: 1800,
            7: 6300,
            8: 16800,
            9: 37800,
            10: 75600,
            11: 138600,
            12: 237600,
            13: 386100,
            14: 600600,
            15: 900900,
        },
    ),
    "mais-milionaria": LotteryConfig(
        slug="mais-milionaria",
        display_name="+Milionaria",
        api_modalidade="+Milionária",
        api_path="maismilionaria",
        min_value=1,
        max_value=50,
        picks=6,
        min_picks=6,
        max_picks=12,
        zero_padded_width=2,
        special_label="Trevos",
        special_min=1,
        special_max=6,
        special_picks=2,
        min_special_picks=2,
        max_special_picks=6,
        special_width=1,
        price_table={
            (6, 2): 600,
            (6, 3): 1800,
            (6, 4): 3600,
            (6, 5): 6000,
            (6, 6): 9000,
            (7, 2): 4200,
            (7, 3): 12600,
            (7, 4): 25200,
            (7, 5): 42000,
            (7, 6): 63000,
            (8, 2): 16800,
            (8, 3): 50400,
            (8, 4): 100800,
            (8, 5): 168000,
            (8, 6): 252000,
            (9, 2): 50400,
            (9, 3): 151200,
            (9, 4): 302400,
            (9, 5): 504000,
            (9, 6): 756000,
            (10, 2): 126000,
            (10, 3): 378000,
            (10, 4): 756000,
            (10, 5): 1260000,
            (10, 6): 1890000,
            (11, 2): 277200,
            (11, 3): 831600,
            (11, 4): 1663200,
            (11, 5): 2772000,
            (11, 6): 4158000,
            (12, 2): 554400,
            (12, 3): 1663200,
            (12, 4): 3326400,
            (12, 5): 5544000,
            (12, 6): 8316000,
        },
    ),
    "lotomania": LotteryConfig(
        slug="lotomania",
        display_name="Lotomania",
        api_modalidade="Lotomania",
        api_path="lotomania",
        min_value=0,
        max_value=99,
        picks=50,
        min_picks=50,
        max_picks=50,
        zero_padded_width=2,
        price_table={50: 300},
    ),
    "dupla-sena": LotteryConfig(
        slug="dupla-sena",
        display_name="Dupla Sena",
        api_modalidade="Dupla Sena",
        api_path="duplasena",
        min_value=1,
        max_value=50,
        picks=6,
        min_picks=6,
        max_picks=15,
        zero_padded_width=2,
        price_table={
            6: 300,
            7: 2100,
            8: 8400,
            9: 25200,
            10: 63000,
            11: 138600,
            12: 277200,
            13: 514800,
            14: 900900,
            15: 1501500,
        },
    ),
    "dia-de-sorte": LotteryConfig(
        slug="dia-de-sorte",
        display_name="Dia de Sorte",
        api_modalidade="Dia de Sorte",
        api_path="diadesorte",
        min_value=1,
        max_value=31,
        picks=7,
        min_picks=7,
        max_picks=15,
        zero_padded_width=2,
        special_label="Mes da sorte",
        special_values=MONTHS,
        special_picks=1,
        min_special_picks=1,
        max_special_picks=1,
        price_table={
            7: 250,
            8: 2000,
            9: 9000,
            10: 30000,
            11: 82500,
            12: 198000,
            13: 429000,
            14: 858000,
            15: 1608750,
        },
    ),
    "supersete": LotteryConfig(
        slug="supersete",
        display_name="SuperSete",
        api_modalidade="Super Sete",
        api_path="supersete",
        min_value=0,
        max_value=0,
        picks=0,
        min_picks=0,
        max_picks=0,
        zero_padded_width=1,
        columns=7,
        digits_per_column=1,
        min_digits_per_column=1,
        max_digits_per_column=3,
        price_table={
            7: 300,
            8: 600,
            9: 1200,
            10: 2400,
            11: 4800,
            12: 9600,
            13: 19200,
            14: 38400,
            15: 57600,
            16: 86400,
            17: 129600,
            18: 194400,
            19: 291600,
            20: 437400,
            21: 656100,
        },
    ),
}

ALIASES = {
    "mega": "mega-sena",
    "megasena": "mega-sena",
    "lotofacil": "lotofacil",
    "lotofácil": "lotofacil",
    "maismilionaria": "mais-milionaria",
    "+milionaria": "mais-milionaria",
    "+milionária": "mais-milionaria",
    "milionaria": "mais-milionaria",
    "milionária": "mais-milionaria",
    "lotomania": "lotomania",
    "duplasena": "dupla-sena",
    "dia": "dia-de-sorte",
    "dia-de-sorte": "dia-de-sorte",
    "supersete": "supersete",
    "super-sete": "supersete",
}


def get_lottery(identifier: str) -> LotteryConfig:
    normalized = identifier.strip().lower()
    key = ALIASES.get(normalized, normalized)
    try:
        return LOTTERIES[key]
    except KeyError as error:
        supported = ", ".join(sorted(LOTTERIES))
        raise ValueError(f"Loteria invalida: {identifier}. Opcoes: {supported}.") from error
