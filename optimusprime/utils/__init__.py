# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Utilities Package
"""
from optimusprime.utils.constants import (
    APP_NAME, APP_SUBTITLE, APP_VERSION, TASK_NAME,
    APP_DIR, REPORT_DIR, BACKUP_DIR, TASK_BACKUP_DIR,
    STARTUP_BACKUP_DIR, ICON_DIR, CONFIG_FILE, LOG_FILE,
    DEFAULT_CONFIG, PROTECTED_PROCESSES, PROTECTED_SERVICE_NAMES,
    DANGEROUS_TASK_PATH_PREFIXES, CREATE_NO_WINDOW
)
from optimusprime.utils.logger import log
from optimusprime.utils.config import CONFIG, load_config, save_config
from optimusprime.utils.elevation import is_admin, elevate_current_script, enable_debug_privilege
from optimusprime.utils.helpers import (
    norm, name_key, fmt_mb, fmt_gb, run_cmd, ps, ps_json,
    icon_cache_path, extract_windows_icon
)
from optimusprime.utils.self_healing import (
    ensure_directories, suppress_console, ensure_dependency, heal_all_dependencies
)

__all__ = [
    "APP_NAME", "APP_SUBTITLE", "APP_VERSION", "TASK_NAME",
    "APP_DIR", "REPORT_DIR", "BACKUP_DIR", "TASK_BACKUP_DIR",
    "STARTUP_BACKUP_DIR", "ICON_DIR", "CONFIG_FILE", "LOG_FILE",
    "DEFAULT_CONFIG", "PROTECTED_PROCESSES", "PROTECTED_SERVICE_NAMES",
    "DANGEROUS_TASK_PATH_PREFIXES", "CREATE_NO_WINDOW",
    "log", "CONFIG", "load_config", "save_config",
    "is_admin", "elevate_current_script", "enable_debug_privilege",
    "norm", "name_key", "fmt_mb", "fmt_gb", "run_cmd", "ps", "ps_json",
    "icon_cache_path", "extract_windows_icon",
    "ensure_directories", "suppress_console", "ensure_dependency", "heal_all_dependencies"
]
