from __future__ import annotations

from collections.abc import Callable, Iterable
import logging
import shutil
from urllib.parse import urlparse

from playwright.async_api import Browser, Page, Playwright, async_playwright

from palpiteiro.automation.caixa_exceptions import CaixaNavigationError, CaixaSelectorError
from palpiteiro.automation.caixa_selectors import (
    CAIXA_ALLOWED_HOSTS,
    CAIXA_MEGA_SENA_URL,
    CAIXA_PORTAL_URL,
    lotofacil_number_selector,
    dupla_sena_number_selector,
    dia_de_sorte_number_selector,
    dia_de_sorte_month_selector,
    super_sete_number_selector,
    lotomania_number_selector,
    mais_milionaria_number_selector,
    mais_milionaria_trevo_selector,
    mega_sena_number_selector,
    quina_number_selector,
)
from palpiteiro.automation.caixa_models import CaixaGame, CaixaTransferState
from palpiteiro.automation.caixa_validation import (
    CaixaValidationError,
    validate_games,
    validate_lotofacil_numbers,
    validate_lotomania_numbers,
    validate_mais_milionaria_numbers,
    validate_mais_milionaria_trevos,
    validate_mega_sena_numbers,
    validate_quina_numbers,
    validate_dupla_sena_numbers,
    validate_dia_de_sorte_numbers,
    validate_dia_de_sorte_month,
    validate_super_sete_numbers,
    verify_numbers,
)

_log = logging.getLogger(__name__)


class CaixaBrowser:
    """Controla apenas a abertura segura do navegador visível para a CAIXA.

    A classe não usa contexto persistente, não manipula credenciais e não executa
    nenhuma ação financeira. A marcação de dezenas será implementada em etapa
    posterior, após validação dos elementos reais do portal.
    """

    def __init__(self) -> None:
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self.page: Page | None = None

    async def __aenter__(self) -> "CaixaBrowser":
        self._playwright = await async_playwright().start()
        executable = self._find_chromium_executable()
        launch_options = {"headless": False}
        if executable is not None:
            launch_options["executable_path"] = executable
        try:
            self._browser = await self._playwright.chromium.launch(**launch_options)
        except Exception as error:
            raise CaixaNavigationError(
                "Não foi possível iniciar um navegador compatível para a CAIXA. "
                "Instale ou atualize o Google Chrome, Chromium ou Microsoft Edge, ou instale o Chromium do Playwright e tente novamente."
            ) from error
        self.page = await self._browser.new_page()
        return self

    @staticmethod
    def _find_chromium_executable() -> str | None:
        """Localiza um navegador Chromium instalado nativamente no Linux."""
        for command in (
            "google-chrome",
            "google-chrome-stable",
            "chromium",
            "chromium-browser",
            "microsoft-edge",
            "microsoft-edge-stable",
        ):
            executable = shutil.which(command)
            if executable:
                return executable
        return None

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()

    @staticmethod
    def is_allowed_url(url: str) -> bool:
        parsed = urlparse(url)
        return parsed.scheme == "https" and parsed.hostname in CAIXA_ALLOWED_HOSTS

    async def open_portal(self) -> Page:
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        await self.page.goto(CAIXA_PORTAL_URL, wait_until="domcontentloaded")
        current_url = self.page.url
        if not self.is_allowed_url(current_url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        page_text = (await self.page.locator("body").inner_text()).lower()
        if "shieldsquare block" in page_text or "comportamento malicioso" in page_text:
            raise CaixaNavigationError(
                "A CAIXA bloqueou o navegador automatizado (ShieldSquare). "
                "Abra o portal oficial manualmente para continuar a conferência."
            )
        return self.page

    async def mark_mega_sena_numbers(self, numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        """Marca um único jogo e confere cada seleção pelo estado real do DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")

        expected = validate_mega_sena_numbers(numbers)
        if not self.page.url.endswith("#/mega-sena"):
            await self.page.goto(CAIXA_MEGA_SENA_URL, wait_until="domcontentloaded")

        for number in expected:
            locator = self.page.locator(mega_sena_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            selected = await locator.evaluate(
                "element => element.classList.contains('selected')"
            )
            if not selected:
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")

        selected_numbers: list[int] = []
        for number in range(1, 61):
            locator = self.page.locator(mega_sena_number_selector(number))
            if await locator.count() == 1 and await locator.evaluate(
                "element => element.classList.contains('selected')"
            ):
                selected_numbers.append(number)
        verify_numbers(expected, selected_numbers)
        return expected

    async def mark_lotofacil_numbers(self, numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        """Marca um único jogo da Lotofácil e confere o estado real do DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        expected = validate_lotofacil_numbers(numbers)
        if not self.page.url.endswith("#/lotofacil"):
            await self.page.goto(
                "https://www.loteriasonline.caixa.gov.br/silce-web/#/lotofacil",
                wait_until="domcontentloaded",
            )
        for number in expected:
            locator = self.page.locator(lotofacil_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")
        selected_numbers: list[int] = []
        for number in range(1, 26):
            locator = self.page.locator(lotofacil_number_selector(number))
            if await locator.count() == 1 and await locator.evaluate(
                "element => element.classList.contains('selected')"
            ):
                selected_numbers.append(number)
        verify_numbers(expected, selected_numbers)
        return expected

    async def mark_quina_numbers(self, numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        """Marca um único jogo da Quina e confere o estado real do DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        expected = validate_quina_numbers(numbers)
        if not self.page.url.endswith("#/quina"):
            await self.page.goto(
                "https://www.loteriasonline.caixa.gov.br/silce-web/#/quina",
                wait_until="domcontentloaded",
            )
        for number in expected:
            locator = self.page.locator(quina_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")
        selected_numbers: list[int] = []
        for number in range(1, 81):
            locator = self.page.locator(quina_number_selector(number))
            if await locator.count() == 1 and await locator.evaluate(
                "element => element.classList.contains('selected')"
            ):
                selected_numbers.append(number)
        verify_numbers(expected, selected_numbers)
        return expected

    async def mark_mais_milionaria_game(
        self, numbers: tuple[int, ...] | list[int], trevos: tuple[int, ...] | list[int]
    ) -> tuple[tuple[int, ...], tuple[int, ...]]:
        """Marca dezenas e trevos de um jogo +Milionária e confere o DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        expected_numbers = validate_mais_milionaria_numbers(numbers)
        expected_trevos = validate_mais_milionaria_trevos(trevos)
        if not self.page.url.endswith("#/mais-milionaria"):
            await self.page.goto(
                "https://www.loteriasonline.caixa.gov.br/silce-web/#/mais-milionaria",
                wait_until="domcontentloaded",
            )
        for number in expected_numbers:
            locator = self.page.locator(mais_milionaria_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")
        for trevo in expected_trevos:
            locator = self.page.locator(mais_milionaria_trevo_selector(trevo))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar o trevo {trevo} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"O trevo {trevo} não foi confirmado como selecionado.")
        selected_numbers = [
            number
            for number in range(1, 51)
            if await self.page.locator(mais_milionaria_number_selector(number)).evaluate(
                "element => element.classList.contains('selected')"
            )
        ]
        selected_trevos = [
            trevo
            for trevo in range(1, 7)
            if await self.page.locator(mais_milionaria_trevo_selector(trevo)).evaluate(
                "element => element.classList.contains('selected')"
            )
        ]
        verify_numbers(expected_numbers, selected_numbers)
        verify_numbers(expected_trevos, selected_trevos)
        return expected_numbers, expected_trevos

    async def mark_lotomania_numbers(self, numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        """Marca um único jogo da Lotomania e confere o estado real do DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        expected = validate_lotomania_numbers(numbers)
        if not self.page.url.endswith("#/lotomania"):
            await self.page.goto(
                "https://www.loteriasonline.caixa.gov.br/silce-web/#/lotomania",
                wait_until="domcontentloaded",
            )
        for number in expected:
            locator = self.page.locator(lotomania_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")
        selected_numbers = [
            number
            for number in range(100)
            if await self.page.locator(lotomania_number_selector(number)).evaluate(
                "element => element.classList.contains('selected')"
            )
        ]
        verify_numbers(expected, selected_numbers)
        return expected

    async def mark_dupla_sena_numbers(self, numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        """Marca um único jogo da Dupla Sena e confere o estado real do DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        expected = validate_dupla_sena_numbers(numbers)
        if not self.page.url.endswith("#/dupla-sena"):
            await self.page.goto(
                "https://www.loteriasonline.caixa.gov.br/silce-web/#/dupla-sena",
                wait_until="domcontentloaded",
            )
        for number in expected:
            locator = self.page.locator(dupla_sena_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")
        selected_numbers = [
            number
            for number in range(1, 51)
            if await self.page.locator(dupla_sena_number_selector(number)).evaluate(
                "element => element.classList.contains('selected')"
            )
        ]
        verify_numbers(expected, selected_numbers)
        return expected

    async def mark_dia_de_sorte_game(self, numbers: tuple[int, ...] | list[int], month: str) -> tuple[int, ...]:
        """Marca dezenas e o Mês da Sorte, conferindo o estado do DOM."""
        if self.page is None:
            raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
        if not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação saiu do domínio oficial autorizado da CAIXA.")
        expected = validate_dia_de_sorte_numbers(numbers)
        expected_month = validate_dia_de_sorte_month(month)
        if not self.page.url.endswith("#/dia-de-sorte"):
            await self.page.goto("https://www.loteriasonline.caixa.gov.br/silce-web/#/dia-de-sorte", wait_until="domcontentloaded")
        for number in expected:
            locator = self.page.locator(dia_de_sorte_number_selector(number))
            if await locator.count() != 1:
                raise CaixaSelectorError(f"Não foi possível localizar a dezena {number:02d} no volante.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"):
                raise CaixaSelectorError(f"A dezena {number:02d} não foi confirmada como selecionada.")
        month_locator = self.page.locator(dia_de_sorte_month_selector(expected_month))
        if await month_locator.count() != 1:
            raise CaixaSelectorError(f"Não foi possível localizar o mês {expected_month} no volante.")
        await month_locator.click()
        if not await month_locator.evaluate("element => element.classList.contains('active')"):
            raise CaixaSelectorError(f"O mês {expected_month} não foi confirmado como selecionado.")
        selected_numbers = [number for number in range(1, 32) if await self.page.locator(dia_de_sorte_number_selector(number)).evaluate("element => element.classList.contains('selected')")]
        verify_numbers(expected, selected_numbers)
        return expected

    async def mark_super_sete_numbers(self, numbers: tuple[int, ...] | list[int]) -> tuple[int, ...]:
        if self.page is None or not self.is_allowed_url(self.page.url):
            raise CaixaNavigationError("A navegação da CAIXA não está disponível.")
        expected = validate_super_sete_numbers(numbers)
        if not self.page.url.endswith("#/super-sete"):
            await self.page.goto("https://www.loteriasonline.caixa.gov.br/silce-web/#/super-sete", wait_until="domcontentloaded")
        for number in expected:
            locator = self.page.locator(super_sete_number_selector(number))
            if await locator.count() != 1: raise CaixaSelectorError(f"Não foi possível localizar a opção {number}.")
            await locator.click()
            if not await locator.evaluate("element => element.classList.contains('selected')"): raise CaixaSelectorError(f"A opção {number} não foi confirmada.")
        selected = [number for number in range(1, 71) if await self.page.locator(super_sete_number_selector(number)).evaluate("element => element.classList.contains('selected')")]
        verify_numbers(expected, selected)
        return expected

    async def prepare_mega_sena_games(
        self,
        games: Iterable[CaixaGame],
        progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos sequencialmente, sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        total = len(validated_games)
        prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()):
                _log.info("Transferência CAIXA cancelada antes do jogo %d de %d", index, total)
                break
            if progress is not None:
                progress(index, total, CaixaTransferState.TRANSFERRING)
            _log.info("Iniciando preparação do jogo %d de %d", index, total)

            if self.page is None:
                raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            selected = await self.page.locator("a.selected").allTextContents({"timeoutMs": 5000})
            if selected:
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() != 1:
                    raise CaixaSelectorError("Não foi possível limpar o volante antes do próximo jogo.")
                await clear_button.click()

            await self.mark_mega_sena_numbers(game.numbers)
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            if await complete_button.count() != 1:
                raise CaixaSelectorError("Não foi possível localizar o comando de preparação do jogo.")
            await complete_button.click()
            prepared += 1
            _log.info("Jogo %d de %d preparado para conferência", index, total)
            if progress is not None:
                progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_lotofacil_games(
        self,
        games: Iterable[CaixaGame],
        progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos da Lotofácil sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        if any(game.lottery_slug != "lotofacil" for game in validated_games):
            raise CaixaValidationError("A lista contém uma modalidade diferente de Lotofácil.")
        total = len(validated_games)
        prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()):
                break
            if progress is not None:
                progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None:
                raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count():
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() != 1:
                    raise CaixaSelectorError("Não foi possível limpar o volante antes do próximo jogo.")
                await clear_button.click()
            await self.mark_lotofacil_numbers(game.numbers)
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            if await complete_button.count() != 1:
                raise CaixaSelectorError("Não foi possível localizar o comando de preparação do jogo.")
            await complete_button.click()
            prepared += 1
            if progress is not None:
                progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_quina_games(
        self,
        games: Iterable[CaixaGame],
        progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos da Quina sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        if any(game.lottery_slug != "quina" for game in validated_games):
            raise CaixaValidationError("A lista contém uma modalidade diferente de Quina.")
        total = len(validated_games)
        prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()):
                break
            if progress is not None:
                progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None:
                raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count():
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() != 1:
                    raise CaixaSelectorError("Não foi possível limpar o volante antes do próximo jogo.")
                await clear_button.click()
            await self.mark_quina_numbers(game.numbers)
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            if await complete_button.count() != 1:
                raise CaixaSelectorError("Não foi possível localizar o comando de preparação do jogo.")
            await complete_button.click()
            prepared += 1
            if progress is not None:
                progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_mais_milionaria_games(
        self,
        games: Iterable[CaixaGame],
        progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos +Milionária sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        if any(game.lottery_slug != "mais-milionaria" for game in validated_games):
            raise CaixaValidationError("A lista contém uma modalidade diferente de +Milionária.")
        total = len(validated_games)
        prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()):
                break
            if progress is not None:
                progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None:
                raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count() or await self.page.locator(".selected").count():
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() == 1:
                    await clear_button.click()
                clear_trevos = self.page.get_by_role("button", name="Limpar os Trevos", exact=True)
                if await clear_trevos.count() == 1:
                    await clear_trevos.click()
            await self.mark_mais_milionaria_game(game.numbers, tuple(int(value) for value in game.special))
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            complete_trevos = self.page.get_by_role("button", name="Complete os Trevos", exact=True)
            if await complete_button.count() != 1 or await complete_trevos.count() != 1:
                raise CaixaSelectorError("Não foi possível localizar os comandos de preparação da +Milionária.")
            await complete_button.click()
            await complete_trevos.click()
            prepared += 1
            if progress is not None:
                progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_lotomania_games(
        self,
        games: Iterable[CaixaGame],
        progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos da Lotomania sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        if any(game.lottery_slug != "lotomania" for game in validated_games):
            raise CaixaValidationError("A lista contém uma modalidade diferente de Lotomania.")
        total = len(validated_games)
        prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()):
                break
            if progress is not None:
                progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None:
                raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count():
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() != 1:
                    raise CaixaSelectorError("Não foi possível limpar o volante antes do próximo jogo.")
                await clear_button.click()
            await self.mark_lotomania_numbers(game.numbers)
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            if await complete_button.count() != 1:
                raise CaixaSelectorError("Não foi possível localizar o comando de preparação do jogo.")
            await complete_button.click()
            prepared += 1
            if progress is not None:
                progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_dupla_sena_games(
        self,
        games: Iterable[CaixaGame],
        progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos da Dupla Sena sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        if any(game.lottery_slug != "dupla-sena" for game in validated_games):
            raise CaixaValidationError("A lista contém uma modalidade diferente de Dupla Sena.")
        total = len(validated_games)
        prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()):
                break
            if progress is not None:
                progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None:
                raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count():
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() != 1:
                    raise CaixaSelectorError("Não foi possível limpar o volante antes do próximo jogo.")
                await clear_button.click()
            await self.mark_dupla_sena_numbers(game.numbers)
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            if await complete_button.count() != 1:
                raise CaixaSelectorError("Não foi possível localizar o comando de preparação do jogo.")
            await complete_button.click()
            prepared += 1
            if progress is not None:
                progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_dia_de_sorte_games(
        self, games: Iterable[CaixaGame], progress: Callable[[int, int, CaixaTransferState], None] | None = None,
        cancel_event: object | None = None,
    ) -> int:
        """Prepara jogos do Dia de Sorte sem adicioná-los ao carrinho."""
        validated_games = validate_games(games)
        if any(game.lottery_slug != "dia-de-sorte" for game in validated_games):
            raise CaixaValidationError("A lista contém uma modalidade diferente de Dia de Sorte.")
        total = len(validated_games); prepared = 0
        for index, game in enumerate(validated_games, start=1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()): break
            if progress is not None: progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None: raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count():
                clear_button = self.page.get_by_role("button", name="Limpar Volante", exact=True)
                if await clear_button.count() != 1: raise CaixaSelectorError("Não foi possível limpar o volante antes do próximo jogo.")
                await clear_button.click()
            await self.mark_dia_de_sorte_game(game.numbers, str(game.special[0]))
            complete_button = self.page.get_by_role("button", name="Complete o Jogo", exact=True)
            if await complete_button.count() != 1: raise CaixaSelectorError("Não foi possível localizar o comando de preparação do jogo.")
            await complete_button.click(); prepared += 1
            if progress is not None: progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def prepare_super_sete_games(self, games: Iterable[CaixaGame], progress: Callable[[int, int, CaixaTransferState], None] | None = None, cancel_event: object | None = None) -> int:
        validated_games = validate_games(games)
        if any(game.lottery_slug != "supersete" for game in validated_games): raise CaixaValidationError("A lista contém modalidade diferente de Super Sete.")
        prepared = 0; total = len(validated_games)
        for index, game in enumerate(validated_games, 1):
            if cancel_event is not None and bool(getattr(cancel_event, "is_set", lambda: False)()): break
            if progress is not None: progress(index, total, CaixaTransferState.TRANSFERRING)
            if self.page is None: raise CaixaNavigationError("O navegador da CAIXA ainda não foi iniciado.")
            if await self.page.locator("a.selected").count(): await self.page.get_by_role("button", name="Limpar Volante", exact=True).click()
            await self.mark_super_sete_numbers(game.numbers)
            await self.page.get_by_role("button", name="Complete o Jogo", exact=True).click()
            prepared += 1
            if progress is not None: progress(index, total, CaixaTransferState.PREPARED)
        return prepared

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None
        self.page = None
