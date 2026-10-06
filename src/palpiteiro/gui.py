from __future__ import annotations

import sys
import tkinter as tk
import webbrowser
from pathlib import Path
from queue import Empty, Queue
from threading import Thread
from tkinter import filedialog, font as tkfont, messagebox, simpledialog, ttk

from palpiteiro import __version__
from palpiteiro.cli import MENU_ORDER
from palpiteiro.conferencia import compare_saved_report, load_saved_report
from palpiteiro.estrategia import BET_PROFILES, generate_bets
from palpiteiro.exportacao import (
    build_text_report,
    save_text_report,
)
from palpiteiro.pdf_report import create_pdf_report
from palpiteiro.browser import open_pdf
from palpiteiro.historico import StatisticsStore, SyncResult, format_currency
from palpiteiro.loterias import LOTTERIES, LotteryConfig, format_brl_from_cents, get_lottery
from palpiteiro.localizacao import IDIOMAS, traduzir


LOTTERY_LOGO_FILES: dict[str, str] = {
    "mega-sena": "assets/logo-mega-sena.png",
    "lotofacil": "assets/logo-lotofacil.png",
    "quina": "assets/logo-quina.png",
    "mais-milionaria": "assets/logo-mais-milionaria.png",
    "lotomania": "assets/logo-lotomania.png",
    "dupla-sena": "assets/logo-dupla-sena.png",
    "dia-de-sorte": "assets/logo-dia-de-sorte.png",
    "supersete": "assets/logo-supersete.png",
}


class PalpiteiroGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.store = StatisticsStore()
        initial_lottery = LOTTERIES[MENU_ORDER[0]]

        self.selected_lottery = tk.StringVar(value=MENU_ORDER[0])
        self.quantity = tk.IntVar(value=1)
        self.numbers_count = tk.IntVar(value=initial_lottery.picks)
        self.special_count = tk.IntVar(value=initial_lottery.special_picks or 1)
        self.profile = tk.StringVar(value="equilibrado")
        self.language = tk.StringVar(value="pt")
        self.status = tk.StringVar(value="Atualizando resultados oficiais das loterias...")
        self.prize_info = tk.StringVar(value="Proximo premio: aguardando atualizacao oficial...")
        self.price_info = tk.StringVar(value="Valor de referência: aguardando configuração...")

        self.generate_button: ttk.Button | None = None
        self.export_button: ttk.Button | None = None
        self.save_button: ttk.Button | None = None
        self.check_button: ttk.Button | None = None
        self.refresh_button: ttk.Button | None = None
        self.numbers_spin: ttk.Spinbox | None = None
        self.profile_combo: ttk.Combobox | None = None
        self.special_spin: ttk.Spinbox | None = None
        self.special_label: tk.Label | None = None
        self.special_container: tk.Frame | None = None
        self.controls_frame: tk.Frame | None = None
        self.filters_top_frame: tk.Frame | None = None
        self.filters_bottom_frame: tk.Frame | None = None
        self.actions_frame: tk.Frame | None = None
        self.latest_report: dict[str, object] | None = None

        self._sync_thread: Thread | None = None
        self._sync_result: SyncResult | None = None
        self._progress_queue: Queue[tuple[int, int, str]] = Queue()
        self._progress_window: tk.Toplevel | None = None
        self._progress_bar: ttk.Progressbar | None = None
        self._progress_label: tk.Label | None = None
        self._progress_percent: tk.Label | None = None
        self._history_windows: list[tuple[str, tk.Toplevel, tk.Text]] = []
        self._lottery_logo_images: dict[str, tk.PhotoImage] = {}
        self._localized_widgets: dict[str, tk.Widget] = {}
        self._lottery_radios: dict[str, tk.Radiobutton] = {}
        self.language_combo: ttk.Combobox | None = None
        self._subtitle_prefix: tk.Label | None = None
        self._subtitle_link: tk.Label | None = None
        self._subtitle_suffix: tk.Label | None = None

        self._configure_root()
        self._build_layout()
        self._apply_cached_state()
        self._update_output_header()
        self.root.after(50, self._start_sync)
        if self.store.cache_warning:
            self.root.after(100, lambda: messagebox.showwarning("Recuperação do histórico", self.store.cache_warning))

    def _configure_root(self) -> None:
        self.root.title("Palpite Milionário")
        self.root.geometry("1040x620")
        self.root.minsize(960, 540)
        self.root.configure(bg="#f4efe6")
        try:
            self.root.state("zoomed")
        except tk.TclError:
            self.root.attributes("-zoomed", True)
        self._apply_window_icon()

    def _t(self, key: str, fallback: str = "") -> str:
        return traduzir(self.language.get(), key, fallback)

    def _register_text(self, key: str, widget: tk.Widget) -> tk.Widget:
        self._localized_widgets[key] = widget
        return widget

    def _change_language(self, _event: object | None = None) -> None:
        if self.language_combo is not None:
            selected = self.language_combo.get()
            self.language.set(next((code for code, name in IDIOMAS if name == selected), "pt"))
        self.root.title(self._t("app_title"))
        self._refresh_profile_values()
        self._update_subtitle()
        for key, widget in self._localized_widgets.items():
            text = f"{self._t('version')} {__version__}" if key == "version" else self._t(key)
            widget.configure(text=text)
        self._update_output_header()

    def _open_lottery_website(self, _event: object | None = None) -> None:
        webbrowser.open_new_tab("https://www.loteriasonline.caixa.gov.br")

    def _update_subtitle(self) -> None:
        if self._subtitle_prefix is None or self._subtitle_link is None or self._subtitle_suffix is None:
            return
        url = "https://www.loteriasonline.caixa.gov.br"
        subtitle = self._t("subtitle")
        if url in subtitle:
            prefix, suffix = subtitle.split(url, 1)
        else:
            prefix, suffix = f"{subtitle} - ", ""
        self._subtitle_prefix.configure(text=prefix)
        self._subtitle_suffix.configure(text=suffix)

    def _profile_translation_key(self, profile: str) -> str:
        return f"profile_{profile}"

    def _refresh_profile_values(self) -> None:
        if self.profile_combo is None:
            return
        profiles = list(BET_PROFILES)
        self.profile_combo.configure(values=[self._t(self._profile_translation_key(profile)) for profile in profiles])
        self.profile_combo.current(profiles.index(self.profile.get()) if self.profile.get() in profiles else 0)

    def _profile_selected(self, _event: object | None = None) -> None:
        if self.profile_combo is None:
            return
        profiles = list(BET_PROFILES)
        index = self.profile_combo.current()
        if 0 <= index < len(profiles):
            self.profile.set(profiles[index])

    @staticmethod
    def _lottery_translation_key(slug: str) -> str:
        return {"mega-sena": "mega", "lotofacil": "lotofacil", "quina": "quina", "mais-milionaria": "mais", "lotomania": "lotomania", "dupla-sena": "dupla", "dia-de-sorte": "dia", "supersete": "super"}[slug]

    def _resource_path(self, relative_path: str) -> Path:
        base_path = getattr(sys, "_MEIPASS", None)
        if base_path:
            return Path(base_path) / relative_path
        return Path(__file__).resolve().parents[2] / relative_path

    def _load_lottery_logo(self, lottery_slug: str) -> tk.PhotoImage | None:
        relative_path = LOTTERY_LOGO_FILES.get(lottery_slug)
        if relative_path is None:
            return None
        image = self._lottery_logo_images.get(lottery_slug)
        if image is not None:
            return image
        try:
            image = tk.PhotoImage(file=str(self._resource_path(relative_path)))
        except tk.TclError:
            return None
        self._lottery_logo_images[lottery_slug] = image
        return image

    def _lottery_card_width(self, gap: int = 12) -> int:
        screen_width = self.root.winfo_screenwidth()
        available_width = max(1, screen_width - 48)
        return min(190, max(150, (available_width - (len(MENU_ORDER) - 1) * gap) // len(MENU_ORDER)))

    def _lottery_name_font(self, card_width: int, gap: int = 12) -> tuple[str, int]:
        screen_width = self.root.winfo_screenwidth()
        available_width = max(1, screen_width - 48)
        card_width = min(card_width, (available_width - (len(MENU_ORDER) - 1) * gap) // len(MENU_ORDER))
        # Reserve space for the radio indicator, logo and both internal
        # paddings; otherwise Tk clips the final glyph of longer labels.
        text_width = max(1, card_width - 80)
        for size in range(18, 9, -1):
            candidate = tkfont.Font(self.root, family="Segoe UI", size=size)
            if max(candidate.measure(LOTTERIES[key].display_name) for key in MENU_ORDER) <= text_width:
                return ("Segoe UI", size)
        return ("Segoe UI", 10)

    def _apply_window_icon(self) -> None:
        png_path = self._resource_path("assets/app-icon.png")
        ico_path = self._resource_path("assets/app-icon.ico")

        try:
            if png_path.exists():
                self._window_icon = tk.PhotoImage(file=str(png_path))
                self.root.iconphoto(True, self._window_icon)
        except tk.TclError:
            self._window_icon = None

        try:
            if ico_path.exists():
                self.root.iconbitmap(str(ico_path))
        except tk.TclError:
            pass

    def _show_progress_window(self) -> None:
        if self._progress_window is not None and self._progress_window.winfo_exists():
            return

        window = tk.Toplevel(self.root)
        window.title("Atualizando resultados")
        window.resizable(False, False)
        window.configure(bg="#f4efe6")
        window.transient(self.root)
        window.attributes("-topmost", True)
        window.protocol("WM_DELETE_WINDOW", lambda: None)

        frame = tk.Frame(window, bg="#f4efe6", padx=28, pady=24)
        frame.pack(fill="both", expand=True)

        self._progress_label = tk.Label(
            frame,
            text="Iniciando atualização oficial das loterias...",
            font=("Segoe UI Semibold", 12),
            bg="#f4efe6",
            fg="#2b2b2b",
            anchor="w",
            justify="left",
            wraplength=620,
        )
        self._progress_label.pack(fill="x")

        bar_row = tk.Frame(frame, bg="#f4efe6")
        bar_row.pack(fill="x", pady=(10, 0))

        self._progress_bar = ttk.Progressbar(
            bar_row,
            orient="horizontal",
            mode="determinate",
            maximum=len(LOTTERIES),
            length=520,
        )
        self._progress_bar.pack(side="left", fill="x", expand=True)

        self._progress_percent = tk.Label(
            bar_row,
            text="0%",
            font=("Segoe UI Semibold", 12),
            bg="#f4efe6",
            fg="#123524",
            width=6,
            anchor="e",
        )
        self._progress_percent.pack(side="left", padx=(12, 0))

        window.update_idletasks()
        width = max(window.winfo_width(), 700)
        height = max(window.winfo_height(), 150)
        x = self.root.winfo_screenwidth() // 2 - width // 2
        y = self.root.winfo_screenheight() // 2 - height // 2
        window.geometry(f"{width}x{height}+{x}+{y}")
        window.lift()
        window.focus_force()

        self._progress_window = window

    def _update_progress_window(self, current: int, total: int, message: str) -> None:
        if self._progress_window is None or not self._progress_window.winfo_exists():
            return
        if self._progress_label is not None:
            self._progress_label.configure(text=message)
        if self._progress_bar is not None:
            self._progress_bar.configure(maximum=max(total, 1), value=max(0, min(current, total)))
        if self._progress_percent is not None:
            percent = int((max(0, min(current, total)) / max(total, 1)) * 100)
            self._progress_percent.configure(text=f"{percent}%")

    def _close_progress_window(self) -> None:
        if self._progress_window is not None and self._progress_window.winfo_exists():
            self._progress_window.destroy()
        self._progress_window = None
        self._progress_bar = None
        self._progress_label = None
        self._progress_percent = None

    def _build_layout(self) -> None:
        container = tk.Frame(self.root, bg="#f4efe6", padx=24, pady=24)
        container.pack(fill="both", expand=True)

        header = tk.Frame(container, bg="#123524", padx=24, pady=20)
        header.pack(fill="x")
        self._register_text("app_title", tk.Label(
            header,
            text=self._t("app_title"),
            font=("Segoe UI Semibold", 26),
            fg="#f7f2e8",
            bg="#123524",
        )).pack(anchor="w")
        subtitle_frame = tk.Frame(header, bg="#123524")
        subtitle_frame.pack(anchor="w", pady=(4, 0))
        self._subtitle_prefix = tk.Label(
            subtitle_frame,
            font=("Segoe UI", 11),
            fg="#d8e7dc",
            bg="#123524",
        )
        self._subtitle_prefix.pack(side="left")
        self._subtitle_link = tk.Label(
            subtitle_frame,
            text="https://www.loteriasonline.caixa.gov.br",
            font=("Segoe UI", 11, "underline"),
            fg="#b9e4ff",
            bg="#123524",
            cursor="hand2",
        )
        self._subtitle_link.pack(side="left")
        self._subtitle_link.bind("<Button-1>", self._open_lottery_website)
        self._subtitle_suffix = tk.Label(
            subtitle_frame,
            font=("Segoe UI", 11),
            fg="#d8e7dc",
            bg="#123524",
        )
        self._subtitle_suffix.pack(side="left")
        self._update_subtitle()

        language_frame = tk.Frame(header, bg="#123524")
        language_frame.place(relx=1.0, rely=0.0, anchor="ne")
        self._register_text("language", tk.Label(
            language_frame,
            text=self._t("language"),
            font=("Segoe UI Semibold", 10),
            fg="#f7f2e8",
            bg="#123524",
        )).pack(side="left", padx=(0, 8))
        self.language_combo = ttk.Combobox(
            language_frame,
            values=[name for _code, name in IDIOMAS],
            state="readonly",
            width=14,
        )
        self.language_combo.current(0)
        self.language_combo.bind("<<ComboboxSelected>>", self._change_language)
        self.language_combo.pack(side="left")

        menu_frame = tk.Frame(container, bg="#e6dccb", padx=18, pady=18)
        menu_frame.pack(fill="x", pady=(18, 14))

        self._register_text("lotteries", tk.Label(
            menu_frame,
            text=self._t("lotteries"),
            font=("Segoe UI Semibold", 12),
            fg="#123524",
            bg="#e6dccb",
        )).grid(row=0, column=0, sticky="w", pady=(0, 12))

        buttons_frame = tk.Frame(menu_frame, bg="#e6dccb")
        buttons_frame.grid(row=1, column=0, sticky="w")
        lottery_card_width = self._lottery_card_width()
        lottery_name_font = self._lottery_name_font(lottery_card_width)

        for index, key in enumerate(MENU_ORDER):
            config = LOTTERIES[key]
            logo_image = self._load_lottery_logo(key)
            option_cell = tk.Frame(buttons_frame, bg="#ffffff", width=lottery_card_width, height=44)
            option_cell.grid(row=0, column=index, padx=(0, 12), sticky="w")
            option_cell.pack_propagate(False)
            radio = tk.Radiobutton(
                option_cell,
                text=config.display_name,
                image=logo_image,
                compound="left",
                font=lottery_name_font,
                bg="#ffffff",
                fg="#1c1c1c",
                activebackground="#ffffff",
                selectcolor="#ffffff",
                relief="flat",
                bd=0,
                highlightthickness=0,
                anchor="center",
                padx=2,
                value=key,
                variable=self.selected_lottery,
                command=self._update_output_header,
            )
            radio.pack(fill="both", expand=True, anchor="w")
            self._lottery_radios[key] = radio

        controls = tk.Frame(container, bg="#f4efe6")
        controls.pack(fill="x", pady=(0, 14))
        self.controls_frame = controls

        filters_top = tk.Frame(controls, bg="#f4efe6")
        filters_top.pack(fill="x")
        self.filters_top_frame = filters_top

        filters_bottom = tk.Frame(controls, bg="#f4efe6")
        filters_bottom.pack(fill="x", pady=(10, 0))
        self.filters_bottom_frame = filters_bottom

        actions = tk.Frame(controls, bg="#f4efe6")
        actions.pack(fill="x", pady=(10, 0))
        self.actions_frame = actions

        self._register_text("history", ttk.Button(
            filters_top,
            text=self._t("history"),
            command=self.show_history,
        )).pack(side="left", padx=(0, 14))

        self.refresh_button = ttk.Button(
            filters_top,
            text=self._t("refresh"),
            command=self.refresh_statistics,
        )
        self.refresh_button.pack(side="left", padx=(0, 14))

        self._register_text("quantity", tk.Label(
            filters_top,
            text=self._t("quantity"),
            font=("Segoe UI Semibold", 11),
            bg="#f4efe6",
            fg="#2b2b2b",
        )).pack(side="left")

        ttk.Spinbox(
            filters_top,
            from_=1,
            to=100,
            textvariable=self.quantity,
            width=6,
        ).pack(side="left", padx=(10, 16))

        self._register_text("numbers", tk.Label(
            filters_top,
            text=self._t("numbers"),
            font=("Segoe UI Semibold", 11),
            bg="#f4efe6",
            fg="#2b2b2b",
        )).pack(side="left")

        self.numbers_spin = ttk.Spinbox(
            filters_top,
            from_=1,
            to=100,
            textvariable=self.numbers_count,
            width=6,
        )
        self.numbers_spin.pack(side="left", padx=(10, 16))

        self.special_container = tk.Frame(filters_bottom, bg="#f4efe6")
        self.special_container.pack(side="left", padx=(0, 16))

        self._register_text("profile", tk.Label(
            filters_bottom,
            text=self._t("profile"),
            font=("Segoe UI Semibold", 11),
            bg="#f4efe6",
            fg="#2b2b2b",
        )).pack(side="left")

        self.profile_combo = ttk.Combobox(
            filters_bottom,
            values=[self._t(self._profile_translation_key(profile)) for profile in BET_PROFILES],
            state="readonly",
            width=12,
        )
        self.profile_combo.current(list(BET_PROFILES).index(self.profile.get()))
        self.profile_combo.bind("<<ComboboxSelected>>", self._profile_selected)
        self.profile_combo.pack(side="left", padx=(10, 16))

        self.special_label = tk.Label(
            self.special_container,
            text=self._t("special"),
            font=("Segoe UI Semibold", 11),
            bg="#f4efe6",
            fg="#2b2b2b",
        )
        self.special_spin = ttk.Spinbox(
            self.special_container,
            from_=1,
            to=6,
            textvariable=self.special_count,
            width=6,
        )

        self.generate_button = ttk.Button(
            actions,
            text=self._t("generate"),
            command=self.generate_bets,
        )
        self.generate_button.pack(side="left")
        self.generate_button.state(["disabled"])

        self._register_text("clear", ttk.Button(
            actions,
            text=self._t("clear"),
            command=self.clear_output,
        )).pack(side="left", padx=(10, 0))

        self.save_button = ttk.Button(
            actions,
            text=self._t("save"),
            command=self.save_bets_text,
        )
        self.save_button.pack(side="left", padx=(10, 0))
        self.save_button.state(["disabled"])

        self.check_button = ttk.Button(
            actions,
            text=self._t("check"),
            command=self.check_saved_file,
        )
        self.check_button.pack(side="left", padx=(10, 0))

        self.export_button = ttk.Button(
            actions,
            text=self._t("print"),
            command=self.export_pdf,
        )
        self.export_button.pack(side="left", padx=(10, 0))
        self.export_button.state(["disabled"])

        self._localized_widgets.update(
            {
                "generate": self.generate_button,
                "save": self.save_button,
                "check": self.check_button,
                "print": self.export_button,
                "refresh": self.refresh_button,
            }
        )

        prize_frame = tk.Frame(container, bg="#f4efe6")
        prize_frame.pack(fill="x", pady=(0, 14))

        tk.Label(
            prize_frame,
            textvariable=self.prize_info,
            anchor="w",
            font=("Segoe UI Semibold", 11),
            bg="#f4efe6",
            fg="#123524",
        ).pack(fill="x")

        tk.Label(
            prize_frame,
            textvariable=self.price_info,
            anchor="w",
            font=("Segoe UI", 11),
            bg="#f4efe6",
            fg="#2b2b2b",
        ).pack(fill="x", pady=(6, 0))

        output_frame = tk.Frame(container, bg="#1f2937", padx=2, pady=2)
        output_frame.pack(fill="both", expand=True)

        self.output_widget = tk.Text(
            output_frame,
            wrap="word",
            font=("Consolas", 14),
            bg="#fffdf8",
            fg="#1f2937",
            padx=18,
            pady=18,
            relief="flat",
        )
        self.output_widget.pack(fill="both", expand=True)
        self._configure_read_only_text(self.output_widget)
        self.selected_lottery.trace_add("write", self._handle_selection_change)
        self.quantity.trace_add("write", self._handle_selection_change)
        self.numbers_count.trace_add("write", self._handle_selection_change)
        self.special_count.trace_add("write", self._handle_selection_change)
        self.profile.trace_add("write", self._handle_selection_change)

        status_bar = tk.Frame(self.root, bg="#e6dccb", padx=24, pady=8, highlightbackground="#d1c3aa", highlightthickness=1)
        status_bar.pack(side="bottom", fill="x")

        tk.Label(
            status_bar,
            textvariable=self.status,
            anchor="w",
            justify="left",
            font=("Segoe UI", 10),
            bg="#e6dccb",
            fg="#4b5563",
        ).pack(fill="x")

        version_badge = self._register_text("version", tk.Label(
            self.root,
            text=f"{self._t('version')} {__version__}",
            anchor="e",
            justify="right",
            font=("Segoe UI Semibold", 10),
            bg="#123524",
            fg="#f8fafc",
            padx=10,
            pady=4,
            bd=1,
            relief="solid",
        ))
        version_badge.place(relx=1.0, rely=1.0, x=-18, y=-14, anchor="se")

    def _configure_read_only_text(self, widget: tk.Text) -> None:
        widget.configure(takefocus=True, insertwidth=0)
        widget.bind("<Button-1>", lambda _event, target=widget: (target.focus_set(), None)[1], add="+")
        widget.bind("<Key>", self._handle_read_only_keypress)
        widget.bind("<<Paste>>", lambda _event: "break")
        widget.bind("<<Cut>>", lambda _event: "break")
        widget.bind("<Control-Home>", lambda _event, target=widget: self._jump_to_start(target))
        widget.bind("<Control-End>", lambda _event, target=widget: self._jump_to_end(target))
        widget.bind("<Prior>", lambda _event, target=widget: self._page_up(target))
        widget.bind("<Next>", lambda _event, target=widget: self._page_down(target))
        widget.bind("<Page_Up>", lambda _event, target=widget: self._page_up(target))
        widget.bind("<Page_Down>", lambda _event, target=widget: self._page_down(target))

    def _jump_to_start(self, widget: tk.Text) -> str:
        widget.mark_set("insert", "1.0")
        widget.see("1.0")
        return "break"

    def _has_cached_statistics(self) -> bool:
        return any(self.store.has_statistics(slug) for slug in LOTTERIES)

    def _apply_cached_state(self) -> None:
        if self.generate_button is not None and self._has_cached_statistics():
            self.generate_button.state(["!disabled"])
            self.status.set("Cache local carregado. Atualizando resultados oficiais em segundo plano...")

    def _jump_to_end(self, widget: tk.Text) -> str:
        widget.mark_set("insert", "end-1c")
        widget.see("end-1c")
        return "break"

    def _page_up(self, widget: tk.Text) -> str:
        widget.yview_scroll(-1, "page")
        return "break"

    def _page_down(self, widget: tk.Text) -> str:
        widget.yview_scroll(1, "page")
        return "break"

    def _handle_read_only_keypress(self, event: tk.Event) -> str | None:
        navigation_keys = {
            "Up",
            "Down",
            "Left",
            "Right",
            "Home",
            "End",
            "Prior",
            "Next",
            "Page_Up",
            "Page_Down",
        }
        if event.keysym in navigation_keys:
            return None

        # Allow copy/select shortcuts while blocking editing shortcuts.
        if event.state & 0x4:
            if event.keysym.lower() in {"c", "a", "home", "end"}:
                return None
            return "break"

        if event.keysym in {"Tab", "Shift_L", "Shift_R", "Control_L", "Control_R"}:
            return None

        return "break"

    def _set_output(self, text: str) -> None:
        self.output_widget.delete("1.0", tk.END)
        self.output_widget.insert("1.0", text)

    def _format_bet_output_line(self, lottery: LotteryConfig, index: int, rendered_bet: str) -> str:
        if lottery.slug in {"lotofacil", "mais-milionaria", "lotomania", "dia-de-sorte", "supersete"}:
            return f"Jogo {index}:\n  {rendered_bet}"
        if len(rendered_bet) > 32:
            return f"Jogo {index}:\n  {rendered_bet}"
        return f"Jogo {index}: {rendered_bet}"

    def _configure_inputs_for_lottery(self, lottery: LotteryConfig) -> None:
        self.numbers_count.set(lottery.picks)
        if self.numbers_spin is not None:
            self.numbers_spin.configure(from_=lottery.min_picks, to=lottery.max_picks)

        if self.special_label is None or self.special_spin is None:
            return

        if lottery.slug == "mais-milionaria":
            self.special_count.set(lottery.special_picks)
            self.special_label.configure(text=self._t("trevos"))
            self.special_spin.configure(
                from_=lottery.min_special_picks,
                to=lottery.max_special_picks,
            )
            self.special_label.pack(side="left")
            self.special_spin.pack(side="left", padx=(10, 0))
            return

        if lottery.slug == "supersete":
            self.special_count.set(lottery.digits_per_column)
            self.special_label.configure(text=self._t("numbers_column"))
            self.special_spin.configure(
                from_=lottery.min_digits_per_column,
                to=lottery.max_digits_per_column,
            )
            self.special_label.pack(side="left")
            self.special_spin.pack(side="left", padx=(10, 0))
            return

        self.special_label.pack_forget()
        self.special_spin.pack_forget()

    def _handle_selection_change(self, *_args: object) -> None:
        self._update_price_info()

    def _update_prize_info(self, slug: str) -> None:
        statistics = self.store.get_statistics(slug)
        if not statistics:
            self.prize_info.set(self._t("waiting_prize"))
            return

        lottery = get_lottery(slug)
        prize = format_currency(statistics.get("proximo_premio"))
        next_date = statistics.get("data_proximo_concurso") or "sem data"
        current_contest = statistics.get("concurso_atual") or "?"
        next_contest = statistics.get("concurso_proximo") or "?"
        current_result = self._format_current_contest_result(lottery, statistics, current_contest)
        self.prize_info.set(
            f"{self._t('estimated')}: {prize} | {self._t('next_contest')}: {next_contest} | {self._t('last_contest')}: {current_contest}{current_result}"
        )

    def _format_current_contest_result(
        self,
        lottery: LotteryConfig,
        statistics: dict[str, object],
        current_contest: object,
    ) -> str:
        history = statistics.get("historico")
        if not isinstance(history, list):
            return ""

        current_contest_text = str(current_contest)
        for item in reversed(history):
            if not isinstance(item, dict):
                continue
            if str(item.get("concurso")) != current_contest_text:
                continue
            rendered = lottery.format_bet(item)
            return f" - {self._t('drawn')}: {rendered}"
        return ""

    def _update_price_info(self) -> None:
        lottery = get_lottery(self.selected_lottery.get())
        try:
            quantity = int(self.quantity.get())
        except (tk.TclError, ValueError):
            quantity = 1

        try:
            picks, special_picks, digits_per_column = self._get_current_bet_options(lottery)
            price_per_game = lottery.bet_price_cents(
                picks=picks,
                special_picks=special_picks,
                digits_per_column=digits_per_column,
            )
            total_price = price_per_game * max(quantity, 1)
            self.price_info.set(
                f"{self._t('price_game')}: {format_brl_from_cents(price_per_game)} | {self._t('total')} ({max(quantity, 1)}): {format_brl_from_cents(total_price)}"
            )
        except ValueError as error:
            self.price_info.set(f"{self._t('price_waiting')} {error}")

    def _update_output_header(self) -> None:
        lottery = get_lottery(self.selected_lottery.get())
        self._configure_inputs_for_lottery(lottery)
        self._update_prize_info(lottery.slug)
        self._update_price_info()

        instruction = self._t("click_generate")
        if self._has_cached_statistics():
            instruction = self._t("click_generate")

        self._set_output(f"{lottery.display_name}\n\n{instruction}")

    def clear_output(self) -> None:
        self.quantity.set(1)
        self.latest_report = None
        if self.export_button is not None:
            self.export_button.state(["disabled"])
        if self.save_button is not None:
            self.save_button.state(["disabled"])
        self._update_output_header()
        self.status.set("Tela limpa.")

    def _start_sync(self, force_progress_window: bool = False) -> None:
        if self._sync_thread is not None and self._sync_thread.is_alive():
            self.status.set("Atualizacao oficial em andamento...")
            return

        if self.refresh_button is not None:
            self.refresh_button.state(["disabled"])

        if force_progress_window or not self._has_cached_statistics():
            self._show_progress_window()
        else:
            self.status.set("Atualizando resultados oficiais em segundo plano...")

        self._sync_result = None
        self._sync_thread = Thread(target=self._refresh_statistics, daemon=True)
        self._sync_thread.start()
        self.root.after(200, self._poll_sync_thread)

    def refresh_statistics(self) -> None:
        self._start_sync(force_progress_window=True)

    def _refresh_statistics(self) -> None:
        self._sync_result = self.store.refresh_all(self._queue_progress)

    def _queue_progress(self, current: int, total: int, message: str) -> None:
        self._progress_queue.put((current, total, message))

    def _poll_sync_thread(self) -> None:
        if self._sync_thread is None:
            return

        while True:
            try:
                current, total, message = self._progress_queue.get_nowait()
            except Empty:
                break
            self._update_progress_window(current, total, message)
            self.status.set(message)

        if self._sync_thread.is_alive():
            self.root.after(200, self._poll_sync_thread)
            return

        self._close_progress_window()

        if self.refresh_button is not None:
            self.refresh_button.state(["!disabled"])

        if self._sync_result is None:
            self.status.set("Falha ao atualizar resultados oficiais.")
            return

        base_message = self._sync_result.message

        self.status.set(base_message)
        if self._sync_result.updated_at:
            self.status.set(f"{base_message} Ultima sincronizacao: {self._sync_result.updated_at}")

        if self.generate_button is not None and self._has_cached_statistics():
            self.generate_button.state(["!disabled"])

        self._update_output_header()
        self._refresh_open_history_windows()

    def _get_current_bet_options(self, lottery: LotteryConfig) -> tuple[int | None, int | None, int | None]:
        try:
            picks = int(self.numbers_count.get())
        except (tk.TclError, ValueError):
            raise ValueError("Informe uma quantidade de números válida.")

        if picks < lottery.min_picks or picks > lottery.max_picks:
            raise ValueError(
                f"Essa loteria aceita de {lottery.min_picks} a {lottery.max_picks} números."
            )

        special_picks: int | None = None
        digits_per_column: int | None = None

        if lottery.slug == "mais-milionaria":
            try:
                special_picks = int(self.special_count.get())
            except (tk.TclError, ValueError):
                raise ValueError("Informe uma quantidade de trevos válida.")
            if special_picks < lottery.min_special_picks or special_picks > lottery.max_special_picks:
                raise ValueError(
                    f"A +Milionária aceita de {lottery.min_special_picks} a {lottery.max_special_picks} trevos."
                )

        if lottery.slug == "supersete":
            try:
                digits_per_column = int(self.special_count.get())
            except (tk.TclError, ValueError):
                raise ValueError("Informe quantos números por coluna deseja no SuperSete.")
            if (
                digits_per_column < lottery.min_digits_per_column
                or digits_per_column > lottery.max_digits_per_column
            ):
                raise ValueError(
                    f"O SuperSete aceita de {lottery.min_digits_per_column} a {lottery.max_digits_per_column} números por coluna."
                )

        return picks if lottery.max_picks > 0 else None, special_picks, digits_per_column

    def generate_bets(self) -> None:
        try:
            quantity = int(self.quantity.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Quantidade invalida", "Informe um numero inteiro valido.")
            return

        if quantity < 1:
            messagebox.showerror("Quantidade invalida", "A quantidade deve ser maior que zero.")
            return

        lottery = get_lottery(self.selected_lottery.get())
        try:
            picks, special_picks, digits_per_column = self._get_current_bet_options(lottery)
        except ValueError as error:
            messagebox.showerror("Configuração inválida", str(error))
            return

        price_per_game = lottery.bet_price_cents(
            picks=picks,
            special_picks=special_picks,
            digits_per_column=digits_per_column,
        )
        total_price = price_per_game * quantity

        lines = [
            f"{lottery.display_name}",
            f"Perfil estatistico: {self.profile.get()}",
            f"Preco por jogo: {format_brl_from_cents(price_per_game)}",
            f"Total: {format_brl_from_cents(total_price)}",
            "",
        ]
        rendered_bets: list[str] = []
        raw_bets: list[dict[str, object]] = []
        bets = generate_bets(
            lottery.slug,
            quantity,
            self.store,
            picks=picks,
            special_picks=special_picks,
            digits_per_column=digits_per_column,
            profile=self.profile.get(),
        )
        for index, bet in enumerate(bets, start=1):
            raw_bets.append(bet)
            rendered_bet = lottery.format_bet(bet)
            rendered_bets.append(rendered_bet)
            lines.append(self._format_bet_output_line(lottery, index, rendered_bet))
        prize_line = self.prize_info.get()
        self.latest_report = {
            "lottery": lottery,
            "quantity": quantity,
            "price_per_game": format_brl_from_cents(price_per_game),
            "total_price": format_brl_from_cents(total_price),
            "prize_info": prize_line,
            "profile": self.profile.get(),
            "bets": rendered_bets,
            "structured_bets": raw_bets,
        }
        if self.export_button is not None:
            self.export_button.state(["!disabled"])
        if self.save_button is not None:
            self.save_button.state(["!disabled"])
        self._set_output("\n".join(lines))
        self.status.set(
            f"{quantity} jogo(s) gerado(s) para {lottery.display_name}. Referência total: {format_brl_from_cents(total_price)}."
        )

    def save_bets_text(self) -> None:
        if not self.latest_report:
            messagebox.showinfo("Salvamento indisponível", "Gere palpites antes de salvar.")
            return

        lottery = self.latest_report["lottery"]
        assert isinstance(lottery, LotteryConfig)
        selected_txt = filedialog.asksaveasfilename(
            title="Salvar palpites em TXT",
            defaultextension=".txt",
            initialfile=f"palpite-milionario-{lottery.slug}.txt",
            filetypes=[("Arquivo TXT", "*.txt")],
        )
        if not selected_txt:
            return

        txt_path = Path(selected_txt)
        content = build_text_report(
            lottery,
            self.latest_report["bets"],
            structured_bets=self.latest_report["structured_bets"],
            quantity=int(self.latest_report["quantity"]),
            price_per_game=str(self.latest_report["price_per_game"]),
            total_price=str(self.latest_report["total_price"]),
            prize_info=str(self.latest_report["prize_info"]),
            profile=str(self.latest_report["profile"]),
        )
        save_text_report(content, txt_path)
        self.status.set(f"Palpites salvos em {txt_path}.")

    def export_pdf(self) -> None:
        if not self.latest_report:
            messagebox.showinfo("Exportação indisponível", "Gere palpites antes de exportar.")
            return

        lottery = self.latest_report["lottery"]
        assert isinstance(lottery, LotteryConfig)
        try:
            pdf_path = create_pdf_report(
                lottery,
                self.latest_report["bets"],
                structured_bets=self.latest_report["structured_bets"],
                quantity=int(self.latest_report["quantity"]),
                price_per_game=str(self.latest_report["price_per_game"]),
                total_price=str(self.latest_report["total_price"]),
                prize_info=f"{self.latest_report['prize_info']} | Perfil: {self.latest_report['profile']}",
            )
        except Exception as error:
            messagebox.showerror("Falha ao gerar PDF", f"Não foi possível gerar o relatório: {error}")
            return
        try:
            opened = open_pdf(pdf_path)
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            messagebox.showwarning("PDF gerado", f"Não foi possível abrir o navegador. O PDF está em:\n{pdf_path}")
            return
        self.status.set("PDF aberto para visualização. Use o navegador para salvar uma cópia ou imprimir.")

    def check_saved_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Selecionar PDF, TXT ou HTML com palpites",
            filetypes=[
                ("Arquivos suportados", "*.pdf;*.txt;*.html"),
                ("Arquivo PDF", "*.pdf"),
                ("Arquivo TXT", "*.txt"),
                ("Arquivo HTML", "*.html"),
            ],
        )
        if not selected:
            return

        try:
            report = load_saved_report(Path(selected))
        except Exception as error:
            messagebox.showerror("Conferência", f"Falha ao ler o arquivo informado: {error}")
            return

        default_contest = ""
        statistics = self.store.get_statistics(report.lottery.slug)
        if statistics:
            default_contest = str(statistics.get("concurso_atual") or "")

        contest_raw = simpledialog.askstring(
            "Conferir concurso",
            f"Informe o numero do concurso para {report.lottery.display_name}:",
            initialvalue=default_contest,
            parent=self.root,
        )
        if not contest_raw:
            return

        try:
            contest = int(contest_raw.strip())
        except ValueError:
            messagebox.showerror("Conferência", "Informe um numero de concurso valido.")
            return

        statistics = self.store.get_statistics(report.lottery.slug)
        if not statistics:
            messagebox.showerror("Conferência", "Historico oficial indisponivel para essa loteria.")
            return

        try:
            result_text = compare_saved_report(report, contest, statistics)
        except Exception as error:
            messagebox.showerror("Conferência", str(error))
            return

        self.selected_lottery.set(report.lottery.slug)
        self._set_output(result_text)
        self.status.set(f"Arquivo conferido com sucesso para o concurso {contest}.")

    def show_history(self) -> None:
        lottery = get_lottery(self.selected_lottery.get())
        statistics = self.store.get_statistics(lottery.slug)
        if not statistics:
            messagebox.showinfo("Histórico indisponível", "O histórico ainda não foi carregado.")
            return

        history = statistics.get("historico")
        if not isinstance(history, list) or not history:
            messagebox.showinfo("Histórico indisponível", "Não há histórico disponível para essa loteria.")
            return

        window = tk.Toplevel(self.root)
        window.title(f"Histórico completo - {lottery.display_name}")
        try:
            window.state("zoomed")
        except tk.TclError:
            window.attributes("-zoomed", True)
        window.configure(bg="#f4efe6")

        frame = tk.Frame(window, bg="#f4efe6", padx=16, pady=16)
        frame.pack(fill="both", expand=True)

        text = tk.Text(
            frame,
            wrap="none",
            font=("Consolas", 11),
            bg="#fffdf8",
            fg="#1f2937",
            padx=12,
            pady=12,
        )
        text.pack(fill="both", expand=True)
        self._configure_read_only_text(text)

        vertical = ttk.Scrollbar(frame, orient="vertical", command=text.yview)
        vertical.pack(side="right", fill="y")
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=text.xview)
        horizontal.pack(side="bottom", fill="x")
        text.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

        self._history_windows.append((lottery.slug, window, text))
        self._render_history_text(lottery.slug, text)
        text.focus_set()

    def _render_history_text(self, slug: str, text: tk.Text) -> None:
        lottery = get_lottery(slug)
        statistics = self.store.get_statistics(slug)
        history = statistics.get("historico") if statistics else None

        lines = [f"{lottery.display_name} | Histórico completo", ""]
        if not isinstance(history, list):
            history = []
        for item in history:
            if not isinstance(item, dict):
                continue
            contest = item.get("concurso", "?")
            draw_date = item.get("data_sorteio", "?")
            rendered = lottery.format_bet(item)
            lines.append(f"Concurso {contest} | {draw_date} | {rendered}")

        text.delete("1.0", "end")
        text.insert("1.0", "\n".join(lines))
        text.see("end")

    def _refresh_open_history_windows(self) -> None:
        active_windows: list[tuple[str, tk.Toplevel, tk.Text]] = []
        for slug, window, text in self._history_windows:
            if not window.winfo_exists():
                continue
            self._render_history_text(slug, text)
            active_windows.append((slug, window, text))
        self._history_windows = active_windows


def create_app() -> tk.Tk:
    root = tk.Tk()
    style = ttk.Style(root)
    if "vista" in style.theme_names():
        style.theme_use("vista")
    style.configure("TRadiobutton", font=("Segoe UI", 10))
    style.configure("TButton", font=("Segoe UI Semibold", 10))
    style.configure("TSpinbox", arrowsize=14)
    PalpiteiroGUI(root)
    return root


def launch_gui() -> int:
    root = create_app()
    root.mainloop()
    return 0
