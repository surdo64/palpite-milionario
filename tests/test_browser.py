import base64
import subprocess
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from palpiteiro import browser


def test_linux_nativo_usa_navegador_local(monkeypatch, tmp_path):
    monkeypatch.setattr(browser.platform, "release", lambda: "6.8.0-generic")
    opened = Mock(return_value=True)
    monkeypatch.setattr(browser.webbrowser, "open", opened)
    path = tmp_path / "relatorio.pdf"
    assert browser.open_pdf(path)
    opened.assert_called_once_with(path.as_uri())


def test_wsl_usa_navegador_padrao_windows_com_caminho_seguro(monkeypatch, tmp_path):
    monkeypatch.setattr(browser.platform, "release", lambda: "6.6-microsoft-standard-WSL2")
    monkeypatch.setattr(browser.shutil, "which", lambda name: "/mnt/c/powershell.exe")
    source = r"\\wsl.localhost\Ubuntu\tmp\teste '$();\relatorio.pdf"
    run = Mock(side_effect=[SimpleNamespace(stdout=source + "\n"), SimpleNamespace(returncode=0)])
    monkeypatch.setattr(browser.subprocess, "run", run)
    assert browser.open_pdf(tmp_path / "relatorio.pdf")
    arguments = run.call_args_list[1].args[0]
    script = base64.b64decode(arguments[-1]).decode("utf-16-le")
    assert "UrlAssociations\\https\\UserChoice" in script
    assert source not in script
    assert base64.b64encode(source.encode()).decode() in script
    assert "Copy-Item -LiteralPath" in script
    assert "Set-ItemProperty" not in script


@pytest.mark.parametrize("failure", [subprocess.TimeoutExpired("powershell", 30), subprocess.CalledProcessError(1, "wslpath")])
def test_wsl_falha_controlada(monkeypatch, tmp_path, failure):
    monkeypatch.setattr(browser.platform, "release", lambda: "microsoft-WSL2")
    monkeypatch.setattr(browser.shutil, "which", lambda name: "powershell.exe")
    monkeypatch.setattr(browser.subprocess, "run", Mock(side_effect=failure))
    with pytest.raises(OSError, match="falhou"):
        browser.open_pdf(tmp_path / "relatorio.pdf")
