# Build with the Linux virtual environment, from the project root.
from pathlib import Path
import sys

if sys.platform != "linux":
    raise RuntimeError("Esta configuração deve ser executada no Linux/WSL.")

root = Path(SPECPATH)
a = Analysis(
    [str(root / "src/palpiteiro/__main__.py")],
    pathex=[str(root / "src")],
    binaries=[],
    datas=[(str(root / "assets"), "assets")],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="palpite-milionario", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=True,
)
coll = COLLECT(
    exe, a.binaries, a.datas, strip=False, upx=False, name="palpite-milionario",
)
