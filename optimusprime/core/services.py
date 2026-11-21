# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Windows Service Management with Core Protection
"""
from optimusprime.utils.helpers import ps, ps_json, run_cmd
from optimusprime.utils.logger import log


def get_services() -> list:
    """Enumerate Windows services with classification (Security, Windows, System, Third-party)."""
    data = ps_json(r'''
Get-CimInstance Win32_Service | ForEach-Object {
    $cat = "Other"
    if ($_.Name -in @('WinDefend','WdNisSvc','SecurityHealthService','wscsvc','MpsSvc','BFE') -or $_.DisplayName -like '*Defender*') {
        $cat = 'Security'
    }
    elseif ($_.PathName -match 'Windows|System32|svchost.exe') {
        $cat = 'Windows/Microsoft'
    }
    elseif ($_.StartName -like '*LocalSystem*') {
        $cat = 'System Account'
    } else {
        $cat = 'Third-party'
    }
    [pscustomobject]@{
        Name        = [string]$_.Name
        DisplayName = [string]$_.DisplayName
        State       = [string]$_.State
        StartMode   = [string]$_.StartMode
        StartName   = [string]$_.StartName
        ProcessId   = [int]$_.ProcessId
        Category    = $cat
        Path        = [string]$_.PathName
        Description = [string]$_.Description
    }
} | ConvertTo-Json -Depth 5
''', timeout=90)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def service_action(name: str, action: str):
    """Execute service state or configuration change with safety logging."""
    if action == "start":
        r = run_cmd(["sc.exe", "start", name], timeout=30)
    elif action == "stop":
        r = run_cmd(["sc.exe", "stop", name], timeout=30)
    elif action == "restart":
        r = ps(f"Restart-Service -Name '{name}' -Force -ErrorAction Stop", timeout=40)
    elif action == "automatic":
        r = run_cmd(["sc.exe", "config", name, "start=", "auto"], timeout=30)
    elif action == "delayed":
        r = run_cmd(["sc.exe", "config", name, "start=", "delayed-auto"], timeout=30)
    elif action == "manual":
        r = run_cmd(["sc.exe", "config", name, "start=", "demand"], timeout=30)
    elif action == "disabled":
        r = run_cmd(["sc.exe", "config", name, "start=", "disabled"], timeout=30)
    else:
        return False, "Unknown service action"
    ok = r.returncode == 0
    log(f"Service {action} on '{name}': ok={ok}")
    return ok, (r.stderr or r.stdout).strip()
