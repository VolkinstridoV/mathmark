#!/usr/bin/env python3
"""Запуск настольной версии «Корня» прямо из репозитория."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mathmark.app import main   # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
