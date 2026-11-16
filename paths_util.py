"""Caminhos do app (código-fonte ou .exe PyInstaller)."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def base_dir() -> Path:
    """Pasta do projeto / ao lado do .exe (config, data, uploads)."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundle_dir() -> Path:
    """Recursos empacotados no .exe (_MEIPASS) ou a própria pasta do projeto."""
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", base_dir()))
    return base_dir()


def templates_dir() -> Path:
    base = base_dir()
    local = base / "templates"
    if local.is_dir():
        return local
    return bundle_dir() / "templates"


def static_dir() -> Path:
    base = base_dir()
    local = base / "static"
    if local.is_dir():
        return local
    return bundle_dir() / "static"
