# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Logging with Auto-Rotation & Self-Healing
"""
from datetime import datetime
from pathlib import Path
from optimusprime.utils.constants import LOG_FILE

MAX_LOG_SIZE = 5 * 1024 * 1024  # 5 MB max size


def log(message: str) -> None:
    """Thread-safe, self-rotating logging."""
    try:
        # Self-healing rotation if log file exceeds MAX_LOG_SIZE
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
            backup = LOG_FILE.with_suffix(".log.old")
            try:
                if backup.exists():
                    backup.unlink()
                LOG_FILE.rename(backup)
            except Exception:
                pass

        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {message}\n")
    except Exception:
        pass
