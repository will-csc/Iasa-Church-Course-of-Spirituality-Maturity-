"""Contas de fiéis criadas pelo Apóstolo (persistidas em JSON)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any


def _norm(value: str) -> str:
    return (value or "").strip().casefold()


class UserStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write({"users": {}})

    def _read(self) -> dict[str, Any]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"users": {}}

    def _write(self, data: dict[str, Any]) -> None:
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def list_users(self) -> list[str]:
        with self._lock:
            users = self._read().get("users", {})
            return sorted(users.keys(), key=str.casefold)

    def create(self, name: str, password: str) -> tuple[bool, str]:
        key = (name or "").strip()
        if not key:
            return False, "Informe um nome."
        if not password:
            return False, "Informe uma senha."
        if len(key) < 2:
            return False, "O nome precisa ter pelo menos 2 caracteres."
        with self._lock:
            data = self._read()
            users = data.setdefault("users", {})
            for existing in users:
                if _norm(existing) == _norm(key):
                    return False, "Este nome já existe. Escolha outro."
            users[key] = password
            self._write(data)
            return True, "Conta criada."

    def upsert(self, name: str, password: str) -> None:
        """Cria ou atualiza senha (usado para contas iniciais)."""
        key = (name or "").strip()
        if not key or not password:
            return
        with self._lock:
            data = self._read()
            users = data.setdefault("users", {})
            target = None
            for existing in users:
                if _norm(existing) == _norm(key):
                    target = existing
                    break
            if target is not None:
                del users[target]
            users[key] = password
            self._write(data)

    def authenticate(self, name: str, password: str) -> bool:
        with self._lock:
            users = self._read().get("users", {})
            for existing, stored in users.items():
                if _norm(existing) == _norm(name) and _norm(stored) == _norm(password):
                    return True
            return False

    def resolve_display_name(self, name: str) -> str | None:
        with self._lock:
            users = self._read().get("users", {})
            for existing in users:
                if _norm(existing) == _norm(name):
                    return existing
            return None

    def delete(self, name: str) -> tuple[bool, str]:
        key = (name or "").strip()
        with self._lock:
            data = self._read()
            users = data.setdefault("users", {})
            target = None
            for existing in users:
                if _norm(existing) == _norm(key):
                    target = existing
                    break
            if target is None:
                return False, "Conta não encontrada."
            del users[target]
            self._write(data)
            return True, "Conta removida."
