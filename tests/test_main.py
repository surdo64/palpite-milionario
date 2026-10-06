from palpiteiro import __version__
import pytest

from palpiteiro.gui import PalpiteiroGUI
from palpiteiro.historico import SyncResult
from palpiteiro.loterias import LOTTERIES, format_brl_from_cents, get_lottery
from palpiteiro.main import main


def test_versao_segue_formato_esperado() -> None:
    assert __version__ == "2026.04.080"


def test_catalogo_contem_todas_as_loterias_suportadas() -> None:
    assert set(LOTTERIES) == {
        "mega-sena",
        "lotofacil",
        "quina",
        "mais-milionaria",
        "lotomania",
        "dupla-sena",
        "dia-de-sorte",
        "supersete",
    }


def test_alias_resolve_loteria() -> None:
    assert get_lottery("mega").slug == "mega-sena"
    assert get_lottery("lotofácil").slug == "lotofacil"
    assert get_lottery("+milionária").slug == "mais-milionaria"


def test_precos_oficiais_sao_resolvidos() -> None:
    assert LOTTERIES["mega-sena"].bet_price_cents(6) == 600
    assert LOTTERIES["mais-milionaria"].bet_price_cents(7, 3) == 12600
    assert LOTTERIES["supersete"].bet_price_cents(digits_per_column=2) == 38400
    assert format_brl_from_cents(1608750) == "R$16.087,50"


def test_main_lista_loterias(capsys) -> None:
    exit_code = main(["--listar"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Mega-Sena" in captured.out
    assert "SuperSete" in captured.out


def test_main_exibe_versao(capsys) -> None:
    exit_code = main(["--versao"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out.strip() == __version__


def test_main_gera_palpite_para_mega_sena(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        "palpiteiro.cli.StatisticsStore.refresh_all",
        lambda self: SyncResult(True, False, "Resultados atualizados.", "18/04/2026 22:00:00"),
    )
    monkeypatch.setattr(
        "palpiteiro.cli.StatisticsStore.get_statistics",
        lambda self, slug: {
            "proximo_premio": 70000000.0,
            "data_proximo_concurso": "23/04/2026",
            "concurso_proximo": 2999,
        },
    )
    monkeypatch.setattr(
        "palpiteiro.cli.generate_bets",
        lambda slug, quantity, store, **kwargs: [{"numbers": (1, 2, 3, 4, 5, 6)}],
    )

    exit_code = main(["mega-sena", "--quantidade", "1", "--perfil", "conservador"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Mega-Sena" in captured.out
    assert "Resultados atualizados." in captured.out
    assert "Proximo premio estimado: R$70.000.000,00 | Proximo concurso: 2999 em 23/04/2026" in captured.out
    assert "Perfil estatistico: conservador" in captured.out
    assert "Preco por jogo: R$6,00 | Total: R$6,00" in captured.out
    assert "Jogo 1:" in captured.out


def test_main_chama_gui_quando_nao_recebe_argumentos(monkeypatch) -> None:
    invoked = {"gui": False}

    def fake_launch_gui() -> int:
        invoked["gui"] = True
        return 0

    monkeypatch.setattr("palpiteiro.main.launch_gui", fake_launch_gui)

    exit_code = main([])

    assert exit_code == 0
    assert invoked["gui"] is True


def test_gui_liberaria_geracao_com_cache_local() -> None:
    class FakeStore:
        def has_statistics(self, slug: str) -> bool:
            return slug == "mega-sena"

    assert any(FakeStore().has_statistics(slug) for slug in LOTTERIES)


def test_cartoes_das_loterias_reservam_largura_para_rotulos() -> None:
    class FakeRoot:
        def winfo_screenwidth(self) -> int:
            return 1920

    gui = object.__new__(PalpiteiroGUI)
    gui.root = FakeRoot()

    assert gui._lottery_card_width() == 190


def test_gui_nao_exibe_popup_de_progresso_quando_cache_ja_existe() -> None:
    events: list[str] = []

    class FakeRoot:
        def after(self, _delay: int, callback) -> None:
            events.append(callback.__name__)

    class FakeThread:
        def __init__(self, target, daemon: bool) -> None:
            assert daemon is True
            self.target = target

        def start(self) -> None:
            events.append("thread_started")

    class FakeGUI:
        root = FakeRoot()
        _sync_thread = None
        refresh_button = None
        status = type("Status", (), {"set": lambda self, value: events.append(value)})()

        def _has_cached_statistics(self) -> bool:
            return True

        def _show_progress_window(self) -> None:
            events.append("show_progress")

        def _refresh_statistics(self) -> None:
            events.append("refresh")

        def _poll_sync_thread(self) -> None:
            events.append("poll")

    original_thread = PalpiteiroGUI._start_sync.__globals__["Thread"]
    PalpiteiroGUI._start_sync.__globals__["Thread"] = FakeThread
    try:
        PalpiteiroGUI._start_sync(FakeGUI())
    finally:
        PalpiteiroGUI._start_sync.__globals__["Thread"] = original_thread

    assert "show_progress" not in events
    assert "thread_started" in events
    assert "_poll_sync_thread" in events
    assert "Atualizando resultados oficiais em segundo plano..." in events


def test_gui_atualizacao_manual_exibe_popup_de_progresso() -> None:
    events: list[str] = []

    class FakeGUI:
        def _start_sync(self, force_progress_window: bool = False) -> None:
            events.append(str(force_progress_window))

    PalpiteiroGUI.refresh_statistics(FakeGUI())

    assert "True" in events


def test_gui_agenda_sincronizacao_apos_montar_layout() -> None:
    scheduled: list[tuple[int, str]] = []

    class FakeRoot:
        def after(self, delay: int, callback) -> None:
            scheduled.append((delay, callback.__name__))

    original_configure_root = PalpiteiroGUI._configure_root
    original_build_layout = PalpiteiroGUI._build_layout
    original_apply_cached_state = PalpiteiroGUI._apply_cached_state
    original_update_output_header = PalpiteiroGUI._update_output_header
    original_string_var = PalpiteiroGUI.__init__.__globals__["tk"].StringVar
    original_int_var = PalpiteiroGUI.__init__.__globals__["tk"].IntVar
    try:
        PalpiteiroGUI._configure_root = lambda self: None
        PalpiteiroGUI._build_layout = lambda self: None
        PalpiteiroGUI._apply_cached_state = lambda self: None
        PalpiteiroGUI._update_output_header = lambda self: None
        PalpiteiroGUI.__init__.__globals__["tk"].StringVar = lambda value=None: value
        PalpiteiroGUI.__init__.__globals__["tk"].IntVar = lambda value=None: value
        gui = PalpiteiroGUI(FakeRoot())
    finally:
        PalpiteiroGUI._configure_root = original_configure_root
        PalpiteiroGUI._build_layout = original_build_layout
        PalpiteiroGUI._apply_cached_state = original_apply_cached_state
        PalpiteiroGUI._update_output_header = original_update_output_header
        PalpiteiroGUI.__init__.__globals__["tk"].StringVar = original_string_var
        PalpiteiroGUI.__init__.__globals__["tk"].IntVar = original_int_var

    assert (50, "_start_sync") in scheduled


def test_format_bet_aceita_dados_vindos_do_cache_json() -> None:
    rendered = LOTTERIES["mega-sena"].format_bet({"numbers": [15, 18, 28, 31, 52, 58]})

    assert rendered == "15 18 28 31 52 58"


def test_gui_redesenha_janela_de_historico_aberta() -> None:
    class FakeStore:
        def get_statistics(self, _slug: str) -> dict[str, object]:
            return {
                "historico": [
                    {
                        "concurso": "3033",
                        "data_sorteio": "19/07/2026",
                        "numbers": [10, 20, 30, 40, 50, 60],
                    }
                ]
            }

    class FakeWindow:
        def winfo_exists(self) -> bool:
            return True

    class FakeText:
        def __init__(self) -> None:
            self.value = "antigo"

        def delete(self, start: str, end: str) -> None:
            assert (start, end) == ("1.0", "end")
            self.value = ""

        def insert(self, start: str, value: str) -> None:
            assert start == "1.0"
            self.value = value

        def see(self, index: str) -> None:
            pass

    class FakeGUI:
        store = FakeStore()

        def __init__(self) -> None:
            self.text = FakeText()
            self._history_windows = [("mega-sena", FakeWindow(), self.text)]

        def _render_history_text(self, slug: str, text: FakeText) -> None:
            PalpiteiroGUI._render_history_text(self, slug, text)

    gui = FakeGUI()
    PalpiteiroGUI._refresh_open_history_windows(gui)

    assert "Concurso 3033 | 19/07/2026 | 10 20 30 40 50 60" in gui.text.value
    assert len(gui._history_windows) == 1


@pytest.mark.parametrize("linux", [False, True])
def test_abertura_historico_continua_apos_maximizacao(monkeypatch, linux):
    import tkinter as tk
    from unittest.mock import Mock
    from palpiteiro import gui

    app = object.__new__(PalpiteiroGUI)
    app.root = Mock()
    app.selected_lottery = Mock(get=lambda: "mega-sena")
    app.store = Mock()
    app.store.get_statistics.return_value = {"historico": [
        {"concurso": "1", "data_sorteio": "06/10/2026", "numbers": [1, 2, 3, 4, 5, 6]}
    ]}
    app._history_windows = []
    app._configure_read_only_text = Mock()
    window, text = Mock(), Mock()
    if linux:
        window.state.side_effect = tk.TclError("bad argument zoomed")
    monkeypatch.setattr(gui.tk, "Toplevel", Mock(return_value=window))
    monkeypatch.setattr(gui.tk, "Frame", Mock())
    monkeypatch.setattr(gui.tk, "Text", Mock(return_value=text))
    monkeypatch.setattr(gui.ttk, "Scrollbar", Mock())
    app.show_history()
    if linux:
        window.attributes.assert_called_once_with("-zoomed", True)
    else:
        window.attributes.assert_not_called()
    assert "Concurso 1 | 06/10/2026 | 01 02 03 04 05 06" in text.insert.call_args.args[1]
    assert app._history_windows == [("mega-sena", window, text)]
    text.focus_set.assert_called_once()
