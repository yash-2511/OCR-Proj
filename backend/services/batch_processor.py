from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Callable


BatchWorker = Callable[[str, list[str]], None]


@dataclass
class BatchState:
    total: int = 0
    processed: int = 0
    successful: int = 0
    failed: int = 0
    status: str = "queued"
    error: str | None = None
    documents: list[str] = field(default_factory=list)


_BATCHES: dict[str, BatchState] = {}
_LOCK = threading.Lock()


def create_batch(batch_id: str, documents: list[str]) -> None:
    with _LOCK:
        _BATCHES[batch_id] = BatchState(total=len(documents), documents=list(documents))


def get_batch(batch_id: str) -> BatchState | None:
    with _LOCK:
        return _BATCHES.get(batch_id)


def update_batch(batch_id: str, **changes: Any) -> None:
    with _LOCK:
        batch = _BATCHES.setdefault(batch_id, BatchState())
        for key, value in changes.items():
            setattr(batch, key, value)


def start_batch(batch_id: str, documents: list[str], worker: BatchWorker) -> None:
    create_batch(batch_id, documents)

    def _run() -> None:
        update_batch(batch_id, status="running")
        try:
            worker(batch_id, documents)
            update_batch(batch_id, status="done")
        except Exception as exc:
            update_batch(batch_id, status="failed", error=str(exc))

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
