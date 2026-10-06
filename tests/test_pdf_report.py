import shutil
from unittest.mock import Mock

import pytest
from pypdf import PdfReader

from palpiteiro import gui, pdf_report
from palpiteiro.conferencia import load_saved_report
from palpiteiro.loterias import LOTTERIES


@pytest.fixture
def pdf_factory(tmp_path, monkeypatch):
    # Keep generated test documents isolated from the user's temporary files.
    original = pdf_report.tempfile.mkdtemp
    monkeypatch.setattr(pdf_report.tempfile, "mkdtemp", lambda **kwargs: original(dir=tmp_path, **kwargs))

    def create(bets, **kwargs):
        return pdf_report.create_pdf_report(
            LOTTERIES["mega-sena"], bets,
            structured_bets=[{"numbers": [1, 2, 3, 4, 5, 6]} for _ in bets],
            quantity=len(bets), price_per_game="R$ 6,00", total_price="R$ 12,00",
            prize_info="Próximo prêmio: informação disponível após atualização. " * kwargs.get("repeat", 1),
        )
    return create


@pytest.mark.parametrize("count", [0, 1, 180])
def test_pdf_real_com_paginacao_e_acentos(pdf_factory, count):
    path = pdf_factory(["01 02 03 04 05 06"] * count)
    reader = PdfReader(path)
    text = "\n".join(page.extract_text() for page in reader.pages)
    assert "Palpite Milionário" in text
    assert "Próximo prêmio" in text
    assert "R$ 12,00" in text
    assert len(reader.pages) > 1 if count == 180 else len(reader.pages) == 1
    for number, page in enumerate(reader.pages, 1):
        assert f"Página {number}" in page.extract_text()
        assert float(page.mediabox.width) == pytest.approx(595.28, abs=0.1)
    if count:
        assert len(load_saved_report(path).bets) == count
    else:
        assert "Nenhum palpite disponível" in text


def test_pdf_texto_longo_e_copia_independente(pdf_factory, tmp_path):
    path = pdf_factory(["01 02 03 04 05 06 " * 30], repeat=20)
    copied = tmp_path / "copia.pdf"
    shutil.copyfile(path, copied)
    assert load_saved_report(copied).bets == [{"numbers": [1, 2, 3, 4, 5, 6]}]
    assert "após atualização" in "".join(page.extract_text() for page in PdfReader(path).pages)


def test_pdfs_temporarios_nao_sobrescrevem(pdf_factory):
    first = pdf_factory([])
    second = pdf_factory([])
    assert first != second
    assert first.exists() and second.exists()
    assert first.parent.stat().st_mode & 0o777 == 0o700


def test_gui_abre_pdf_no_navegador(monkeypatch, tmp_path):
    app = Mock()
    app.latest_report = dict(lottery=LOTTERIES["mega-sena"], bets=[], structured_bets=[], quantity=0,
                             price_per_game="R$ 6,00", total_price="R$ 0,00", prize_info="", profile="equilibrado")
    path = tmp_path / "relatorio.pdf"
    monkeypatch.setattr(gui, "create_pdf_report", Mock(return_value=path))
    browser = Mock(return_value=True)
    monkeypatch.setattr(gui, "open_pdf", browser)
    gui.PalpiteiroGUI.export_pdf(app)
    browser.assert_called_once_with(path)


def test_gui_informa_falha_ao_gerar_pdf(monkeypatch):
    app = Mock()
    app.latest_report = dict(lottery=LOTTERIES["mega-sena"], bets=[], structured_bets=[], quantity=0,
                             price_per_game="", total_price="", prize_info="", profile="")
    monkeypatch.setattr(gui, "create_pdf_report", Mock(side_effect=OSError("Sem espaço")))
    error = Mock()
    monkeypatch.setattr(gui.messagebox, "showerror", error)
    browser = Mock()
    monkeypatch.setattr(gui, "open_pdf", browser)
    gui.PalpiteiroGUI.export_pdf(app)
    error.assert_called_once()
    browser.assert_not_called()
