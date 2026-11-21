# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Maintenance, Cleanup, DISM Health & Scheduled Optimization Loop
"""
import os
import shutil
import tempfile
from pathlib import Path
from optimusprime.utils.constants import PROTECTED_PROCESSES
from optimusprime.utils.config import CONFIG
from optimusprime.utils.helpers import norm, name_key, ps, run_cmd
from optimusprime.utils.logger import log
from optimusprime.core.processes import get_processes, suspend_process, minimize_pid_set


def cleanup_temp():
    """Clean User and System temporary directories safely."""
    deleted = skipped = 0
    roots = [Path(tempfile.gettempdir()), Path(os.environ.get("WINDIR", r"C:\Windows")) / "Temp"]
    for root in roots:
        try:
            if not root.exists():
                continue
            for item in root.iterdir():
                try:
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                    deleted += 1
                except Exception:
                    skipped += 1
        except Exception:
            skipped += 1
    log(f"TEMP cleanup completed: deleted={deleted}, skipped={skipped}")
    return deleted, skipped


def flush_dns() -> bool:
    """Flush Windows DNS Resolver Cache."""
    r = run_cmd(["ipconfig.exe", "/flushdns"], timeout=15)
    ok = r.returncode == 0
    log(f"DNS flush: ok={ok}")
    return ok


def refresh_explorer() -> bool:
    """Gracefully restart Windows Explorer shell."""
    r = ps(
        "Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force; "
        "Start-Process explorer.exe", timeout=20
    )
    ok = r.returncode == 0
    log(f"Explorer shell restart: ok={ok}")
    return ok


def empty_recycle_bin() -> bool:
    """Empty Windows Recycle Bin across all drives."""
    r = ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", timeout=30)
    ok = r.returncode == 0
    log(f"Recycle Bin purge: ok={ok}")
    return ok


def component_cleanup():
    """Run DISM StartComponentCleanup on Windows Component Store."""
    r = run_cmd(["DISM.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"], timeout=600)
    ok = r.returncode == 0
    log(f"DISM component store cleanup: ok={ok}")
    return ok, (r.stdout or r.stderr)[-2500:]


def scheduled_optimization():
    """Self-healing background task execution for non-interactive maintenance."""
    log("Scheduled background optimizer run initiated")
    if CONFIG.get("scheduled_clean_temp", True):
        cleanup_temp()
    if CONFIG.get("scheduled_flush_dns", True):
        flush_dns()
    if CONFIG.get("scheduled_auto_sleep", False):
        rules = {name_key(x) for x in CONFIG.get("auto_sleep_processes", []) if norm(x)}
        minimized = minimize_pid_set()
        for row in get_processes():
            pid = int(row.get("PID", 0) or 0)
            pname = name_key(row.get("Name"))
            if pid and pname in rules and pid in minimized and pname not in PROTECTED_PROCESSES:
                ok, detail = suspend_process(pid)
                log(f"Background sleep {pname} (PID {pid}): ok={ok} {detail}")
    log("Scheduled background optimizer run completed successfully")
