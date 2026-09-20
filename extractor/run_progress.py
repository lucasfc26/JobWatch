"""Acompanhamento em tempo real de uma execução do extrator (etapas, log e captura de tela)."""

from __future__ import annotations

import sys
import threading
import time
import uuid
from typing import Any

STEP_DEFINITIONS: tuple[tuple[str, str], ...] = (
    ("launch", "Abrir o Camoufox"),
    ("navigate", "Acessar hiring.amazon.com"),
    ("overlays", "Fechar pop-ups e avisos"),
    ("zip", "Preencher CEP / endereço"),
    ("hours", "Ajustar horas por semana"),
    ("schedule", "Selecionar turnos"),
    ("length", "Informar duração"),
    ("when", "Escolher data de início"),
    ("title", "Preencher nome da vaga"),
    ("results", "Aguardar a lista filtrar"),
    ("collect", "Ler os cards das vagas"),
    ("details", "Abrir detalhes das vagas"),
    ("filter", "Aplicar filtros e normalizar"),
    ("close", "Fechar o Camoufox"),
)

_MAX_LOG_LINES = 600
_LOG_PREFIXES = ("[warehouse]", "[camoufox]")
_local = threading.local()


def _now_ms() -> int:
    return int(time.time() * 1000)


class RunProgress:
    def __init__(self, filters: dict[str, Any], headless: bool) -> None:
        self.id = uuid.uuid4().hex[:12]
        self.filters = filters
        self.headless = headless
        self.status = "queued"
        self.error: str | None = None
        self.jobs: list[dict[str, str]] = []
        self.started_at = _now_ms()
        self.finished_at: int | None = None
        self.steps: list[dict[str, Any]] = [
            {"key": key, "label": label, "status": "pending", "detail": "", "startedAt": None, "endedAt": None}
            for key, label in STEP_DEFINITIONS
        ]
        self.logs: list[dict[str, Any]] = []
        self.page: Any = None
        self._frame: bytes | None = None
        self.frame_version = 0
        self._partial = ""
        self._lock = threading.RLock()

    def _step(self, key: str) -> dict[str, Any]:
        for step in self.steps:
            if step["key"] == key:
                return step
        raise KeyError(key)

    def begin(self, key: str, detail: str = "") -> None:
        if key == "close":
            self.page = None
        else:
            self.shot()
        with self._lock:
            for step in self.steps:
                if step["status"] == "running":
                    step["status"] = "done"
                    step["endedAt"] = _now_ms()
            step = self._step(key)
            step["status"] = "running"
            step["detail"] = detail
            step["startedAt"] = _now_ms()
            step["endedAt"] = None

    def detail(self, text: str) -> None:
        with self._lock:
            for step in self.steps:
                if step["status"] == "running":
                    step["detail"] = text

    def skip(self, *keys: str, detail: str = "") -> None:
        with self._lock:
            for key in keys:
                step = self._step(key)
                if step["status"] == "pending":
                    step["status"] = "skipped"
                    step["detail"] = detail

    def finish(self, key: str) -> None:
        with self._lock:
            step = self._step(key)
            if step["status"] == "running":
                step["status"] = "done"
                step["endedAt"] = _now_ms()

    def shot(self) -> None:
        page = self.page
        if page is None:
            return
        try:
            data = page.screenshot(type="jpeg", quality=55, timeout=3_000)
        except Exception:
            return
        with self._lock:
            self._frame = data
            self.frame_version += 1

    def frame(self) -> bytes | None:
        with self._lock:
            return self._frame

    def append_log(self, line: str) -> None:
        with self._lock:
            self.logs.append({"ts": _now_ms(), "line": line})
            if len(self.logs) > _MAX_LOG_LINES:
                del self.logs[: len(self.logs) - _MAX_LOG_LINES]

    def feed(self, text: str) -> None:
        self._partial += text
        while "\n" in self._partial:
            line, self._partial = self._partial.split("\n", 1)
            line = line.strip()
            if line.startswith(_LOG_PREFIXES):
                self.append_log(line)

    def fail(self, message: str) -> None:
        with self._lock:
            self.error = message
            for step in self.steps:
                if step["status"] == "running":
                    step["status"] = "error"
                    step["detail"] = message[:240]
                    step["endedAt"] = _now_ms()

    def complete(self, jobs: list[dict[str, str]]) -> None:
        with self._lock:
            self.jobs = jobs
            self.status = "error" if self.error else "done"
            self.finished_at = _now_ms()
            for step in self.steps:
                if step["status"] == "running":
                    step["status"] = "done"
                    step["endedAt"] = _now_ms()
                elif step["status"] == "pending" and not self.error:
                    step["status"] = "skipped"

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "id": self.id,
                "status": self.status,
                "headless": self.headless,
                "error": self.error,
                "filters": self.filters,
                "startedAt": self.started_at,
                "finishedAt": self.finished_at,
                "steps": [dict(step) for step in self.steps],
                "logs": list(self.logs),
                "jobs": list(self.jobs),
                "frameVersion": self.frame_version,
            }


def bind(progress: RunProgress | None) -> None:
    _local.progress = progress


def current() -> RunProgress | None:
    return getattr(_local, "progress", None)


def begin(key: str, detail: str = "") -> None:
    tracker = current()
    if tracker:
        tracker.begin(key, detail)


def detail(text: str) -> None:
    tracker = current()
    if tracker:
        tracker.detail(text)


def skip(*keys: str, detail: str = "") -> None:
    tracker = current()
    if tracker:
        tracker.skip(*keys, detail=detail)


def finish(key: str) -> None:
    tracker = current()
    if tracker:
        tracker.finish(key)


def set_page(page: Any) -> None:
    tracker = current()
    if tracker:
        tracker.page = page


def fail(message: str) -> None:
    tracker = current()
    if tracker:
        tracker.fail(message)


class _StdoutTee:
    def __init__(self, inner: Any) -> None:
        self._inner = inner

    def write(self, text: str) -> int:
        tracker = current()
        if tracker:
            tracker.feed(text)
        return self._inner.write(text)

    def flush(self) -> None:
        self._inner.flush()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


def install_stdout_tee() -> None:
    if not isinstance(sys.stdout, _StdoutTee):
        sys.stdout = _StdoutTee(sys.stdout)
