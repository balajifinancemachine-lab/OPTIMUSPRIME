# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Core Functionality Package
"""
from optimusprime.core.system import (
    get_memory, get_system_info, get_drives, get_performance_sample
)
from optimusprime.core.processes import (
    get_processes, minimize_pid_set, suspend_process, resume_process,
    trim_working_set, terminate_pids
)
from optimusprime.core.services import (
    get_services, service_action
)
from optimusprime.core.tasks import (
    get_tasks, task_category, full_task_name, backup_task_xml,
    delete_task, task_enable, task_run, create_optimizer_task
)
from optimusprime.core.startup import (
    get_startup, startup_backup_name, disable_startup, enable_startup
)
from optimusprime.core.network import (
    get_network_adapters, get_tcp_connections
)
from optimusprime.core.apps import (
    get_installed_apps
)
from optimusprime.core.maintenance import (
    cleanup_temp, flush_dns, refresh_explorer, empty_recycle_bin,
    component_cleanup, scheduled_optimization
)

__all__ = [
    "get_memory", "get_system_info", "get_drives", "get_performance_sample",
    "get_processes", "minimize_pid_set", "suspend_process", "resume_process",
    "trim_working_set", "terminate_pids",
    "get_services", "service_action",
    "get_tasks", "task_category", "full_task_name", "backup_task_xml",
    "delete_task", "task_enable", "task_run", "create_optimizer_task",
    "get_startup", "startup_backup_name", "disable_startup", "enable_startup",
    "get_network_adapters", "get_tcp_connections",
    "get_installed_apps",
    "cleanup_temp", "flush_dns", "refresh_explorer", "empty_recycle_bin",
    "component_cleanup", "scheduled_optimization"
]
