from __future__ import annotations

import sys
from typing import Sequence

from palpiteiro.cli import run_cli
from palpiteiro.gui import launch_gui


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_cli(args)
    return launch_gui()


if __name__ == "__main__":
    raise SystemExit(main())
