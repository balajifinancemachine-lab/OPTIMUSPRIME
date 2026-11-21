# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Constants and Environment Definitions
"""
import os
import subprocess
from pathlib import Path

APP_NAME = "OPTIMUSPRIME"
APP_SUBTITLE = "ULTIMATE SYSTEM OPTIMIZER & CONTROLLER"
APP_VERSION = "2.0.0"
TASK_NAME = "OptimusPrime-AutoMaintenance"

APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "OptimusPrime"
REPORT_DIR = APP_DIR / "reports"
BACKUP_DIR = APP_DIR / "backups"
TASK_BACKUP_DIR = BACKUP_DIR / "scheduled_tasks"
STARTUP_BACKUP_DIR = BACKUP_DIR / "startup"
ICON_DIR = APP_DIR / "icons"
CONFIG_FILE = APP_DIR / "settings.json"
LOG_FILE = APP_DIR / "optimusprime.log"

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

DEFAULT_CONFIG = {
    "refresh_seconds": 5,
    "auto_sleep_enabled": False,
    "auto_sleep_after_minutes": 10,
    "auto_sleep_processes": ["msedge.exe"],
    "scheduled_auto_sleep": False,
    "scheduled_clean_temp": True,
    "scheduled_flush_dns": True,
    "theme": "dark",
    "last_page": "Dashboard",
}

PROTECTED_PROCESSES = {
    "system", "idle", "registry", "secure system", "smss", "csrss",
    "wininit", "services", "lsass", "winlogon", "fontdrvhost", "dwm",
    "sihost", "ctfmon", "runtimebroker", "taskhostw", "explorer",
    "startmenuexperiencehost", "searchhost", "applicationframehost",
    "spoolsv", "audiodg", "textinputhost", "widgets",
    "shellexperiencehost", "securityhealthservice", "securityhealthsystray",
    "msmpeng", "smartscreen", "logonui", "userinit", "python", "pythonw",
    "powershell", "pwsh", "cmd", "conhost", "optimusprime"
}

PROTECTED_SERVICE_NAMES = {
    "WinDefend", "WdNisSvc", "SecurityHealthService", "wscsvc",
    "MpsSvc", "BFE", "EventLog", "RpcSs", "RpcEptMapper", "DcomLaunch",
    "SamSs", "LSM", "PlugPlay", "Power", "ProfSvc", "Winmgmt",
    "Schedule", "TermService", "LanmanServer", "LanmanWorkstation"
}

DANGEROUS_TASK_PATH_PREFIXES = (
    "\\Microsoft\\Windows\\", "\\Microsoft\\Office\\"
)
