# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Self-Healing Engine: Dependencies, Directory Integrity & Process Environment
"""
import sys
import ctypes
from pathlib import Path
from optimusprime.utils.constants import (
    APP_DIR, REPORT_DIR, BACKUP_DIR, TASK_BACKUP_DIR,
    STARTUP_BACKUP_DIR, ICON_DIR
)
from optimusprime.utils.logger import log
from optimusprime.utils.helpers import run_cmd


def ensure_directories() -> bool:
    """Self-healing: ensure all necessary working directories exist."""
    folders = [APP_DIR, REPORT_DIR, BACKUP_DIR, TASK_BACKUP_DIR, STARTUP_BACKUP_DIR, ICON_DIR]
    all_ok = True
    for folder in folders:
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            log(f"Self-healing error creating directory {folder}: {exc}")
            all_ok = False
    return all_ok


def suppress_console() -> None:
    """Hide console window if running under python.exe instead of pythonw.exe."""
    if sys.platform == "win32" and "--scheduled-optimize" not in sys.argv:
        try:
            hwnd = ctypes.windll.kernel32.GetConsoleWindow()
            if hwnd:
                ctypes.windll.user32.ShowWindow(hwnd, 0)
        except Exception:
            pass


def ensure_dependency(package: str, import_name: str = None) -> bool:
    """Self-healing: verify package import or install automatically via pip."""
    import_name = import_name or package
    try:
        __import__(import_name)
        return True
    except Exception:
        pass

    log(f"Self-healing: dependency '{package}' not found. Attempting automatic installation...")
    try:
        result = run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", package], timeout=240)
        if result.returncode == 0:
            __import__(import_name)
            log(f"Self-healing: successfully installed and loaded '{package}'")
            return True
        log(f"pip install failed for {package}: {result.stderr[-500:]}")
    except Exception as exc:
        log(f"pip install exception for {package}: {exc}")
    return False


def heal_all_dependencies() -> bool:
    """Ensure all required third-party libraries exist and can be imported."""
    ensure_directories()
    ctk_ok = ensure_dependency("customtkinter")
    pillow_ok = ensure_dependency("Pillow", "PIL")
    return ctk_ok and pillow_ok
