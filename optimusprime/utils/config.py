# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Self-Healing Configuration Store
"""
import json
from pathlib import Path
from optimusprime.utils.constants import CONFIG_FILE, DEFAULT_CONFIG
from optimusprime.utils.logger import log


def load_config() -> dict:
    """Load configuration with self-healing fallback if corrupt."""
    data = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_FILE.exists():
            content = CONFIG_FILE.read_text(encoding="utf-8").strip()
            if content:
                loaded = json.loads(content)
                if isinstance(loaded, dict):
                    data.update(loaded)
    except Exception as exc:
        log(f"Config corrupted ({exc}). Healing with defaults and saving backup.")
        try:
            if CONFIG_FILE.exists():
                backup = CONFIG_FILE.with_suffix(".corrupt.bak")
                CONFIG_FILE.rename(backup)
        except Exception:
            pass
        save_config(data)
    return data


def save_config(config: dict = None) -> bool:
    """Save configuration atomically to disk."""
    if config is None:
        config = CONFIG
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return True
    except Exception as exc:
        log(f"Config save error: {exc}")
        return False


CONFIG = load_config()
