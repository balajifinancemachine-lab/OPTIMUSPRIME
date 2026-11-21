# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Windows Scheduled Tasks Inspection, Safe Backup & Automation
"""
import sys
from datetime import datetime
from pathlib import Path
from optimusprime.utils.constants import TASK_NAME, TASK_BACKUP_DIR
from optimusprime.utils.helpers import norm, ps_json, run_cmd
from optimusprime.utils.logger import log


def task_category(row: dict) -> str:
    """Categorize scheduled tasks into Microsoft, Optimizer, or Third-Party."""
    path = norm(row.get("TaskPath")).lower()
    author = norm(row.get("Author")).lower()
    if row.get("TaskName") == TASK_NAME:
        return "OPTIMUSPRIME"
    if "\\microsoft\\" in path or "microsoft" in author:
        return "Microsoft"
    if author:
        return "Third-party / Named"
    return "System / Unknown"


def full_task_name(path: str, name: str) -> str:
    """Compute normalized full task identifier (e.g. \\Path\\Name)."""
    p = norm(path or "\\")
    n = norm(name)
    return ("\\" + n) if p == "\\" else p.rstrip("\\") + "\\" + n


def get_tasks() -> list:
    """Retrieve full scheduled tasks list with run level, state, and categorization."""
    data = ps_json(r'''
Get-ScheduledTask | ForEach-Object {
    $i = $null
    try { $i = $_ | Get-ScheduledTaskInfo } catch {}
    $actions = ""
    try { $actions = (($_.Actions | ForEach-Object { $_.Execute + ' ' + $_.Arguments }) -join ' | ') } catch {}
    [pscustomobject]@{
        TaskName    = [string]$_.TaskName
        TaskPath    = [string]$_.TaskPath
        State       = [string]$_.State
        Author      = [string]$_.Principal.UserId
        RunLevel    = [string]$_.Principal.RunLevel
        LastRun     = if ($i) { [string]$i.LastRunTime } else { '' }
        NextRun     = if ($i) { [string]$i.NextRunTime } else { '' }
        Description = [string]$_.Description
        Actions     = $actions
    }
} | ConvertTo-Json -Depth 5
''', timeout=100)
    if not data:
        return []
    rows = [data] if isinstance(data, dict) else data
    for row in rows:
        row["Category"] = task_category(row)
        row["Scope"] = "Microsoft/System" if norm(row.get("TaskPath")).lower().startswith("\\microsoft\\") else "Custom/Other"
        row["OptimizerOwned"] = "Yes" if row.get("TaskName") == TASK_NAME else "No"
    return rows


def backup_task_xml(full_name: str):
    """Export task XML definition to backup directory prior to modification/deletion."""
    safe = full_name.replace("\\", "_").replace("/", "_").strip("_")
    target = TASK_BACKUP_DIR / f"{safe}_{datetime.now():%Y%m%d_%H%M%S_%f}.xml"
    r = run_cmd(["schtasks.exe", "/Query", "/TN", full_name, "/XML"], timeout=30)
    if r.returncode == 0 and r.stdout.strip():
        target.write_text(r.stdout, encoding="utf-8")
        return target
    return None


def delete_task(full_name: str):
    """Safely delete scheduled task with automatic XML backup."""
    backup = backup_task_xml(full_name)
    r = run_cmd(["schtasks.exe", "/Delete", "/TN", full_name, "/F"], timeout=30)
    ok = r.returncode == 0
    log(f"Delete task {full_name}: ok={ok}; backup={backup}")
    return ok, str(backup) if backup else ""


def task_enable(full_name: str, enabled: bool) -> bool:
    """Enable or disable scheduled task."""
    action = "/ENABLE" if enabled else "/DISABLE"
    r = run_cmd(["schtasks.exe", action, "/TN", full_name], timeout=20)
    ok = r.returncode == 0
    log(f"{action} task {full_name}: ok={ok}")
    return ok


def task_run(full_name: str) -> bool:
    """Trigger scheduled task run on-demand."""
    r = run_cmd(["schtasks.exe", "/Run", "/TN", full_name], timeout=20)
    ok = r.returncode == 0
    log(f"Run task {full_name}: ok={ok}")
    return ok


def create_optimizer_task(interval_minutes: int, script_path: str = None):
    """Register or update self-healing background automation task."""
    py = str(Path(sys.executable).resolve())
    script = str(Path(script_path or sys.argv[0]).resolve())
    command = f'"{py}" "{script}" --scheduled-optimize'
    r = run_cmd([
        "schtasks.exe", "/Create", "/TN", TASK_NAME,
        "/SC", "MINUTE", "/MO", str(int(interval_minutes)),
        "/TR", command, "/F"
    ], timeout=30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or "Task Scheduler failed")
    log(f"Created/updated background optimizer task: interval={interval_minutes}m")
