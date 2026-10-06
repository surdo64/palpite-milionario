from __future__ import annotations

import base64
import platform
import shutil
import subprocess
import webbrowser
from pathlib import Path


def open_pdf(path: Path) -> bool:
    """Use the host's default browser under WSL, or the Linux browser otherwise."""
    if "microsoft" not in platform.release().lower():
        return webbrowser.open(path.resolve().as_uri())
    try:
        return _open_windows_pdf(path)
    except subprocess.SubprocessError as error:
        raise OSError("A abertura no navegador do Windows falhou ou excedeu o tempo limite.") from error


def _open_windows_pdf(path: Path) -> bool:
    powershell = shutil.which("powershell.exe")
    if not powershell:
        raise OSError("A integração do WSL com o Windows não está disponível.")
    source = subprocess.run(
        ["wslpath", "-w", str(path.resolve())], check=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    # Only base64 data enters the script; file paths never become PowerShell code.
    encoded_source = base64.b64encode(source.encode("utf-8")).decode("ascii")
    script = r'''
$ErrorActionPreference = 'Stop'
$source = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__SOURCE__'))
$choice = Get-ItemProperty -LiteralPath 'HKCU:\Software\Microsoft\Windows\Shell\Associations\UrlAssociations\https\UserChoice'
$key = 'Registry::HKEY_CLASSES_ROOT\' + $choice.ProgId + '\shell\open\command'
$command = (Get-Item -LiteralPath $key).GetValue('')
if ($command -match '^"([^"\r\n]+\.exe)"') {
    $browserExecutable = $Matches[1]
} elseif ($command -match '^([^"\r\n]+?\.exe)(?:\s|$)') {
    $browserExecutable = $Matches[1]
} else {
    throw 'Não foi possível identificar o executável do navegador padrão.'
}
if (-not (Test-Path -LiteralPath $browserExecutable -PathType Leaf)) {
    throw 'O executável do navegador padrão não foi encontrado.'
}
$directory = Join-Path ([IO.Path]::GetTempPath()) ('palpite-' + [Guid]::NewGuid().ToString('N'))
[IO.Directory]::CreateDirectory($directory) | Out-Null
$destination = Join-Path $directory 'relatorio.pdf'
Copy-Item -LiteralPath $source -Destination $destination -ErrorAction Stop
$uri = ([Uri]$destination).AbsoluteUri
# Opening the report is an explicitly requested visible browser interaction.
Start-Process -FilePath $browserExecutable -ArgumentList ('"' + $uri + '"') -WindowStyle Normal
'''.replace("__SOURCE__", encoded_source)
    encoded_script = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    result = subprocess.run(
        [powershell, "-NoLogo", "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded_script],
        capture_output=True, timeout=30,
    )
    if result.returncode:
        raise OSError("Não foi possível abrir o PDF no navegador padrão do Windows. Verifique o navegador padrão e a integração do WSL.")
    return True
