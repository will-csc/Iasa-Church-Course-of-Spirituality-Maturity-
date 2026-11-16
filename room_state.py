"""Estado compartilhado da sala de reunião (em memória)."""

from __future__ import annotations

import threading
from typing import Any


class RoomState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.pdf_filename: str | None = None
        self.pdf_url: str | None = None
        self.current_page: int = 1  # página sugerida pelo Apóstolo
        self.room_locked: bool = False
        self._default_filename: str | None = None
        self._default_url: str | None = None
        # página -> lista de traços; cada traço = [{x,y} normalizado 0..1]
        self.highlights: dict[int, list[list[dict[str, float]]]] = {}

    def configure_default_pdf(self, filename: str, url: str) -> None:
        with self._lock:
            self._default_filename = filename
            self._default_url = url
            self.pdf_filename = filename
            self.pdf_url = url
            self.current_page = 1
            self.highlights = {}

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return self._snapshot_unlocked()

    def set_page(self, page: int) -> dict[str, Any]:
        with self._lock:
            self.current_page = max(1, int(page))
            return self._snapshot_unlocked()

    def set_pdf(self, filename: str, url: str | None = None) -> dict[str, Any]:
        with self._lock:
            self.pdf_filename = filename
            self.pdf_url = url or f"/uploads/{filename}"
            self.current_page = 1
            self.highlights = {}
            return self._snapshot_unlocked()

    def set_locked(self, locked: bool) -> dict[str, Any]:
        with self._lock:
            self.room_locked = bool(locked)
            return self._snapshot_unlocked()

    def restore_default_pdf(self) -> dict[str, Any]:
        with self._lock:
            self.pdf_filename = self._default_filename
            self.pdf_url = self._default_url
            self.current_page = 1
            self.highlights = {}
            return self._snapshot_unlocked()

    def clear_pdf(self) -> dict[str, Any]:
        return self.restore_default_pdf()

    def add_stroke(self, page: int, stroke: list[dict[str, float]]) -> dict[str, Any]:
        with self._lock:
            page = max(1, int(page))
            cleaned: list[dict[str, float]] = []
            for point in stroke or []:
                try:
                    x = float(point.get("x", 0))
                    y = float(point.get("y", 0))
                except (TypeError, ValueError, AttributeError):
                    continue
                cleaned.append(
                    {
                        "x": min(1.0, max(0.0, x)),
                        "y": min(1.0, max(0.0, y)),
                    }
                )
            if len(cleaned) >= 2:
                self.highlights.setdefault(page, []).append(cleaned)
            return self._snapshot_unlocked()

    def clear_highlights(self, page: int | None = None) -> dict[str, Any]:
        with self._lock:
            if page is None:
                self.highlights = {}
            else:
                self.highlights.pop(int(page), None)
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self) -> dict[str, Any]:
        return {
            "pdf_filename": self.pdf_filename,
            "pdf_url": self.pdf_url,
            "current_page": self.current_page,
            "room_locked": self.room_locked,
            "highlights": {
                str(page): strokes for page, strokes in self.highlights.items()
            },
        }


room = RoomState()
