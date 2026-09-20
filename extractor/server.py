from __future__ import annotations

import os
import threading
import traceback
from collections import OrderedDict
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

import run_progress
from amazon_warehouse import run_amazon_warehouse_search

app = FastAPI(title="JobWatch Warehouse Extractor")
_lock = threading.Lock()
_MAX_RUNS = 10
_runs: OrderedDict[str, run_progress.RunProgress] = OrderedDict()
_runs_guard = threading.Lock()

run_progress.install_stdout_tee()


class ExtractRequest(BaseModel):
    zipCode: str = Field(min_length=2, max_length=120)
    workHours: int | None = None
    schedule: list[str] = Field(default_factory=list)
    length: str | None = None
    whenStart: str | None = None
    jobTitle: str | None = None
    employmentType: str | None = None
    payRateMin: int | None = None
    payRateMax: int | None = None


@app.get("/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.post("/extract")
def extract(body: ExtractRequest) -> dict[str, Any]:
    if not _lock.acquire(blocking=True, timeout=240):
        raise HTTPException(status_code=429, detail="O extrator já está em uma varredura")
    try:
        jobs = run_amazon_warehouse_search(body.model_dump())
        return {"jobs": jobs}
    except HTTPException:
        raise
    except Exception as error:
        traceback.print_exc()
        raise HTTPException(status_code=502, detail=str(error)) from error
    finally:
        _lock.release()


def _execute_run(run: run_progress.RunProgress) -> None:
    run_progress.bind(run)
    run.status = "running"
    jobs: list[dict[str, str]] = []
    try:
        jobs = run_amazon_warehouse_search(run.filters)
    except Exception:
        traceback.print_exc()
    finally:
        run.complete(jobs)
        run_progress.bind(None)
        _lock.release()


@app.post("/runs", status_code=202)
def start_run(body: ExtractRequest) -> dict[str, Any]:
    if not _lock.acquire(blocking=False):
        raise HTTPException(status_code=429, detail="O extrator já está em uma varredura")
    headless = os.environ.get("HEADLESS", "true").lower() != "false"
    run = run_progress.RunProgress(body.model_dump(), headless)
    with _runs_guard:
        _runs[run.id] = run
        while len(_runs) > _MAX_RUNS:
            _runs.popitem(last=False)
    try:
        threading.Thread(target=_execute_run, args=(run,), name=f"run-{run.id}", daemon=True).start()
    except Exception:
        _lock.release()
        raise
    return run.snapshot()


@app.get("/runs/current")
def current_run() -> dict[str, Any] | None:
    with _runs_guard:
        latest = next(reversed(_runs.values()), None)
    return latest.snapshot() if latest else None


def _get_run(run_id: str) -> run_progress.RunProgress:
    with _runs_guard:
        run = _runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Execução não encontrada")
    return run


@app.get("/runs/{run_id}")
def get_run(run_id: str) -> dict[str, Any]:
    return _get_run(run_id).snapshot()


@app.get("/runs/{run_id}/frame")
def get_run_frame(run_id: str) -> Response:
    frame = _get_run(run_id).frame()
    if not frame:
        raise HTTPException(status_code=404, detail="Ainda não há captura de tela")
    return Response(content=frame, media_type="image/jpeg", headers={"Cache-Control": "no-store"})
