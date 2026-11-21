# -*- coding: utf-8 -*-
"""
================================================================================
OPTIMUSPRIME - ULTIMATE STANDALONE & SELF-HEALING SYSTEM OPTIMIZER & CONTROLLER
================================================================================
Single-File Standalone Edition (100% All-Inclusive, Zero External Local Dependencies)
Features:
- Self-Healing: Auto-detects & auto-installs missing dependencies (CustomTkinter, Pillow)
- Self-Healing: Pure Tkinter/TTK fallback mode if offline / pip unavailable
- Self-Healing: Auto-recovers corrupt settings & directory hierarchy
- Self-Healing: Auto-escalates Windows token privileges (SeDebugPrivilege)
- Self-Healing: Native NT API process management & high-DPI scaling
- Auto-Elevates: Automatically requests UAC Administrator access at startup
- Complete Modules: Dashboard, Processes, App Sleep, Tasks, Services, Startup,
  Applications, Network, Performance, Storage, Maintenance, System, Reports, Log
================================================================================
"""

# ── 1. CONSOLE SUPPRESSION (SELF-HEALING) ──────────────────────────────────────
import os
import sys
import json
import csv
import time
import shutil
import ctypes
import hashlib
import tempfile
import threading
import subprocess
from pathlib import Path
from datetime import datetime

if sys.platform == "win32" and "--scheduled-optimize" not in sys.argv:
    try:
        _hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if _hwnd:
            ctypes.windll.user32.ShowWindow(_hwnd, 0)
    except Exception:
        pass

# ── 2. CONSTANTS & PATH INTEGRITY ─────────────────────────────────────────────
APP_NAME = "OPTIMUSPRIME"
APP_SUBTITLE = "ULTIMATE SYSTEM CONTROLLER"
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
MAX_LOG_SIZE = 5 * 1024 * 1024

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

# ── 3. SELF-HEALING DIRECTORIES & LOGGING ──────────────────────────────────────
for _f in (APP_DIR, REPORT_DIR, BACKUP_DIR, TASK_BACKUP_DIR, STARTUP_BACKUP_DIR, ICON_DIR):
    try:
        _f.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def log(msg: str):
    try:
        if LOG_FILE.exists() and LOG_FILE.stat().st_size > MAX_LOG_SIZE:
            old = LOG_FILE.with_suffix(".log.old")
            try:
                if old.exists():
                    old.unlink()
                LOG_FILE.rename(old)
            except Exception:
                pass
        with LOG_FILE.open("a", encoding="utf-8") as fh:
            fh.write(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}\n")
    except Exception:
        pass


def load_config() -> dict:
    data = dict(DEFAULT_CONFIG)
    try:
        if CONFIG_FILE.exists():
            content = CONFIG_FILE.read_text(encoding="utf-8").strip()
            if content:
                loaded = json.loads(content)
                if isinstance(loaded, dict):
                    data.update(loaded)
    except Exception as exc:
        log(f"Self-healing corrupt config: {exc}")
        try:
            if CONFIG_FILE.exists():
                CONFIG_FILE.rename(CONFIG_FILE.with_suffix(".corrupt.bak"))
        except Exception:
            pass
        save_config(data)
    return data


def save_config(cfg: dict = None) -> bool:
    if cfg is None:
        cfg = CONFIG
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return True
    except Exception as exc:
        log(f"Config save error: {exc}")
        return False


CONFIG = load_config()

# ── 4. UAC AUTO-ELEVATION & PRIVILEGE ESCALATION ──────────────────────────────
def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def enable_debug_privilege() -> bool:
    try:
        advapi32 = ctypes.windll.advapi32
        kernel32 = ctypes.windll.kernel32

        class LUID(ctypes.Structure):
            _fields_ = [("LowPart", ctypes.c_ulong), ("HighPart", ctypes.c_long)]

        class LUID_AND_ATTRIBUTES(ctypes.Structure):
            _fields_ = [("Luid", LUID), ("Attributes", ctypes.c_ulong)]

        class TOKEN_PRIVILEGES(ctypes.Structure):
            _fields_ = [("PrivilegeCount", ctypes.c_ulong), ("Privileges", LUID_AND_ATTRIBUTES * 1)]

        h_token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(kernel32.GetCurrentProcess(), 0x0020 | 0x0008, ctypes.byref(h_token)):
            return False

        luid = LUID()
        if not advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid)):
            kernel32.CloseHandle(h_token)
            return False

        tp = TOKEN_PRIVILEGES()
        tp.PrivilegeCount = 1
        tp.Privileges[0].Luid = luid
        tp.Privileges[0].Attributes = 0x00000002

        ok = advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), 0, None, None)
        kernel32.CloseHandle(h_token)
        return bool(ok)
    except Exception:
        return False


def elevate_current_script() -> bool:
    try:
        script = str(Path(sys.argv[0]).resolve())
        args = [script] + [a for a in sys.argv[1:] if a != "--elevated"]
        command_line = subprocess.list2cmdline(args)
        rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, command_line, None, 1)
        return rc > 32
    except Exception as exc:
        log(f"Elevation error: {exc}")
        return False


# Auto-elevate if not scheduled background mode
if __name__ == "__main__" and "--scheduled-optimize" not in sys.argv:
    enable_debug_privilege()
    if not is_admin() and "--elevated" not in sys.argv:
        if elevate_current_script():
            sys.exit(0)

# ── 5. SELF-HEALING DEPENDENCY BOOTSTRAP ───────────────────────────────────────
def run_cmd(args, timeout=30):
    try:
        return subprocess.run(
            args, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        class Failed:
            returncode = -1
            stdout = ""
            stderr = str(exc)
        return Failed()


def ensure_dependency(pkg: str, mod: str = None) -> bool:
    mod = mod or pkg
    try:
        __import__(mod)
        return True
    except Exception:
        pass
    log(f"Self-healing: installing missing dependency '{pkg}'...")
    try:
        res = run_cmd([sys.executable, "-m", "pip", "install", "--upgrade", pkg], timeout=240)
        if res.returncode == 0:
            __import__(mod)
            log(f"Successfully installed '{pkg}'")
            return True
    except Exception as exc:
        log(f"pip install exception for {pkg}: {exc}")
    return False


# Bootstrap GUI dependencies
HAS_CTK = ensure_dependency("customtkinter")
HAS_PIL = ensure_dependency("Pillow", "PIL")

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

if HAS_CTK:
    import customtkinter as ctk
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
else:
    ctk = None

if HAS_PIL:
    from PIL import Image
else:
    Image = None

# ── 6. NATIVE POWERSHELL & SYSTEM HELPERS ─────────────────────────────────────
def norm(v) -> str:
    return str(v if v is not None else "").strip()


def name_key(v) -> str:
    return norm(v).lower().replace(".exe", "")


def fmt_mb(v) -> str:
    try:
        return f"{float(v):,.1f}"
    except Exception:
        return "0.0"


def fmt_gb(v) -> str:
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return "0.00"


def ps(script: str, timeout: int = 30):
    return run_cmd(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout,
    )


def ps_json(script: str, timeout: int = 30):
    res = ps(script, timeout)
    if res.returncode != 0 or not res.stdout.strip():
        return None
    try:
        return json.loads(res.stdout.strip())
    except Exception:
        return None


def extract_windows_icon(exe_path: str, size: int = 32):
    if not exe_path or not Path(exe_path).exists():
        return None
    digest = hashlib.sha1(f"{exe_path}|{size}".encode("utf-8", errors="ignore")).hexdigest()
    target = ICON_DIR / f"{digest}.png"
    if target.exists():
        return target
    escaped = str(exe_path).replace("'", "''")
    escaped_target = str(target).replace("'", "''")
    script = f'''
Add-Type -AssemblyName System.Drawing
try {{
    $i = [System.Drawing.Icon]::ExtractAssociatedIcon('{escaped}')
    if ($i) {{
        $b = New-Object System.Drawing.Bitmap {size},{size}
        $g = [System.Drawing.Graphics]::FromImage($b)
        $g.Clear([System.Drawing.Color]::Transparent)
        $g.DrawIcon($i, 0, 0)
        $b.Save('{escaped_target}', [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $b.Dispose(); $i.Dispose()
    }}
}} catch {{}}
'''
    try:
        ps(script, 12)
        if target.exists():
            return target
    except Exception:
        pass
    return None

# ── 7. SYSTEM DATA COLLECTORS ──────────────────────────────────────────────────
def get_memory() -> dict:
    data = ps_json(r'''
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
    TotalGB = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
    FreeGB  = [math]::Round($os.FreePhysicalMemory/1MB, 2)
    UsedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 2)
    UsedPct = [math]::Round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize)*100, 1)
} | ConvertTo-Json -Compress
''', 20)
    return data or {}


def get_system_info() -> dict:
    data = ps_json(r'''
$cs = Get-CimInstance Win32_ComputerSystem
$os = Get-CimInstance Win32_OperatingSystem
$cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
[pscustomobject]@{
    Computer          = $env:COMPUTERNAME
    Manufacturer      = $cs.Manufacturer
    Model             = $cs.Model
    OS                = $os.Caption
    Version           = $os.Version
    Build             = $os.BuildNumber
    Architecture      = $os.OSArchitecture
    RAM_GB            = [math]::Round($cs.TotalPhysicalMemory/1GB, 2)
    LogicalProcessors = $cs.NumberOfLogicalProcessors
    Processor         = $cpu.Name
    MaxClockMHz       = $cpu.MaxClockSpeed
    User              = $env:USERNAME
    BootTime          = [string]$os.LastBootUpTime
} | ConvertTo-Json -Compress
''', 30)
    return data or {}


def get_drives() -> list:
    data = ps_json(r'''
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" |
Select-Object DeviceID,
    @{N="UsedGB"; E={[math]::Round(($_.Size - $_.FreeSpace)/1GB, 2)}},
    @{N="FreeGB"; E={[math]::Round($_.FreeSpace/1GB, 2)}},
    @{N="TotalGB"; E={[math]::Round($_.Size/1GB, 2)}},
    FileSystem, VolumeName |
ConvertTo-Json -Depth 3
''', 30)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def get_performance_sample() -> dict:
    data = ps_json(r'''
$cpu = (Get-Counter '\Processor(_Total)\% Processor Time' -ErrorAction SilentlyContinue).CounterSamples.CookedValue
$mem = Get-CimInstance Win32_OperatingSystem
$rx = (Get-NetAdapterStatistics -ErrorAction SilentlyContinue | Measure-Object ReceivedBytes -Sum).Sum
$tx = (Get-NetAdapterStatistics -ErrorAction SilentlyContinue | Measure-Object SentBytes -Sum).Sum
[pscustomobject]@{
    CPU = if ($cpu) { [math]::Round($cpu, 1) } else { 0 }
    RAM = [math]::Round((($mem.TotalVisibleMemorySize - $mem.FreePhysicalMemory)/$mem.TotalVisibleMemorySize)*100, 1)
    Rx  = [math]::Round($rx/1KB, 1)
    Tx  = [math]::Round($tx/1KB, 1)
} | ConvertTo-Json -Compress
''', 20)
    return data or {}


def get_processes() -> list:
    data = ps_json(r'''
$result = foreach($p in Get-CimInstance Win32_Process){
    $owner = ""
    try {
        $o = Invoke-CimMethod -InputObject $p -MethodName GetOwner
        if ($o.ReturnValue -eq 0) { $owner = "$($o.Domain)\$($o.User)" }
    } catch {}
    $ram = 0
    try { $ram = [math]::Round($p.WorkingSetSize/1MB, 1) } catch {}
    $cpu = $null
    try { $cpu = [math]::Round(($p.UserModeTime + $p.KernelModeTime)/10000000, 1) } catch {}
    [pscustomobject]@{
        PID         = [int]$p.ProcessId
        Name        = [string]$p.Name
        Owner       = [string]$owner
        RAM_MB      = $ram
        CPU_s       = $cpu
        SessionId   = [int]$p.SessionId
        Path        = [string]$p.ExecutablePath
        CommandLine = [string]$p.CommandLine
    }
}
$result | ConvertTo-Json -Depth 5
''', 70)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def minimize_pid_set() -> set:
    script = r'''
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WMin {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint pid);
}
"@
$ids = New-Object System.Collections.Generic.List[int]
[WMin]::EnumWindows({param($h,$l)
    if ([WMin]::IsWindowVisible($h) -and [WMin]::IsIconic($h)) {
        [uint32]$pid = 0
        [WMin]::GetWindowThreadProcessId($h, [ref]$pid) | Out-Null
        if ($pid -gt 0) { [void]$ids.Add([int]$pid) }
    }
    return $true
}, [IntPtr]::Zero) | Out-Null
$ids | Select-Object -Unique | ConvertTo-Json
'''
    data = ps_json(script, 30)
    if data is None:
        return set()
    if isinstance(data, list):
        return {int(v) for v in data if str(v).isdigit()}
    try:
        return {int(data)}
    except Exception:
        return set()


# Native process suspension / memory trimming
PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_SET_QUOTA = 0x0100


def suspend_process(pid: int):
    try:
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
        if not h:
            return False, "OpenProcess failed"
        st = ctypes.windll.ntdll.NtSuspendProcess(h)
        ctypes.windll.kernel32.CloseHandle(h)
        return st == 0, f"NTSTATUS={st}"
    except Exception as exc:
        return False, str(exc)


def resume_process(pid: int):
    try:
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
        if not h:
            return False, "OpenProcess failed"
        st = ctypes.windll.ntdll.NtResumeProcess(h)
        ctypes.windll.kernel32.CloseHandle(h)
        return st == 0, f"NTSTATUS={st}"
    except Exception as exc:
        return False, str(exc)


def trim_working_set(pid: int):
    try:
        h = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_QUOTA, False, int(pid))
        if not h:
            return False, "OpenProcess failed"
        fn = ctypes.windll.kernel32.SetProcessWorkingSetSize
        fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
        fn.restype = ctypes.c_bool
        ok = fn(h, ctypes.c_size_t(-1).value, ctypes.c_size_t(-1).value)
        ctypes.windll.kernel32.CloseHandle(h)
        return bool(ok), ""
    except Exception as exc:
        return False, str(exc)


def terminate_pids(pids: list):
    good = 0
    errors = []
    for pid in pids:
        r = run_cmd(["taskkill.exe", "/PID", str(pid), "/F"], 12)
        if r.returncode == 0:
            good += 1
        else:
            errors.append(f"PID {pid}: {(r.stderr or r.stdout).strip()}")
    return good, errors


def get_services() -> list:
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
''', 90)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def service_action(name: str, action: str):
    if action == "start":
        r = run_cmd(["sc.exe", "start", name], 30)
    elif action == "stop":
        r = run_cmd(["sc.exe", "stop", name], 30)
    elif action == "restart":
        r = ps(f"Restart-Service -Name '{name}' -Force -ErrorAction Stop", 40)
    elif action == "automatic":
        r = run_cmd(["sc.exe", "config", name, "start=", "auto"], 30)
    elif action == "delayed":
        r = run_cmd(["sc.exe", "config", name, "start=", "delayed-auto"], 30)
    elif action == "manual":
        r = run_cmd(["sc.exe", "config", name, "start=", "demand"], 30)
    elif action == "disabled":
        r = run_cmd(["sc.exe", "config", name, "start=", "disabled"], 30)
    else:
        return False, "Unknown action"
    ok = r.returncode == 0
    log(f"Service {action} {name}: ok={ok}")
    return ok, (r.stderr or r.stdout).strip()


def full_task_name(p, n):
    p = norm(p or "\\")
    n = norm(n)
    return ("\\" + n) if p == "\\" else p.rstrip("\\") + "\\" + n


def get_tasks() -> list:
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
''', 100)
    if not data:
        return []
    rows = [data] if isinstance(data, dict) else data
    for r in rows:
        path = norm(r.get("TaskPath")).lower()
        author = norm(r.get("Author")).lower()
        if r.get("TaskName") == TASK_NAME:
            r["Category"] = "OPTIMUSPRIME"
        elif "\\microsoft\\" in path or "microsoft" in author:
            r["Category"] = "Microsoft"
        elif author:
            r["Category"] = "Third-party / Named"
        else:
            r["Category"] = "System / Unknown"
        r["Scope"] = "Microsoft/System" if path.startswith("\\microsoft\\") else "Custom/Other"
        r["OptimizerOwned"] = "Yes" if r.get("TaskName") == TASK_NAME else "No"
    return rows


def backup_task_xml(full_name: str):
    safe = full_name.replace("\\", "_").replace("/", "_").strip("_")
    target = TASK_BACKUP_DIR / f"{safe}_{datetime.now():%Y%m%d_%H%M%S_%f}.xml"
    r = run_cmd(["schtasks.exe", "/Query", "/TN", full_name, "/XML"], 30)
    if r.returncode == 0 and r.stdout.strip():
        target.write_text(r.stdout, encoding="utf-8")
        return target
    return None


def delete_task(full_name: str):
    backup = backup_task_xml(full_name)
    r = run_cmd(["schtasks.exe", "/Delete", "/TN", full_name, "/F"], 30)
    ok = r.returncode == 0
    log(f"Delete task {full_name}: ok={ok}; backup={backup}")
    return ok, str(backup) if backup else ""


def task_enable(full_name: str, enabled: bool) -> bool:
    action = "/ENABLE" if enabled else "/DISABLE"
    r = run_cmd(["schtasks.exe", action, "/TN", full_name], 20)
    return r.returncode == 0


def task_run(full_name: str) -> bool:
    r = run_cmd(["schtasks.exe", "/Run", "/TN", full_name], 20)
    return r.returncode == 0


def create_optimizer_task(interval_minutes: int):
    py = str(Path(sys.executable).resolve())
    script = str(Path(sys.argv[0]).resolve())
    command = f'"{py}" "{script}" --scheduled-optimize'
    r = run_cmd([
        "schtasks.exe", "/Create", "/TN", TASK_NAME,
        "/SC", "MINUTE", "/MO", str(int(interval_minutes)),
        "/TR", command, "/F"
    ], 30)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or "Task Scheduler failed")
    log(f"Registered scheduled background task every {interval_minutes} minutes")


def get_startup() -> list:
    data = ps_json(r'''
$items = @()
$keys = @(
    "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run"
)
foreach($k in $keys){
    if (Test-Path $k){
        $p = Get-ItemProperty $k
        foreach($x in $p.PSObject.Properties){
            if ($x.Name -notmatch '^PS'){
                $scope = if ($k -like "HKCU:*") { "Current User" } else { "All Users" }
                $items += [pscustomobject]@{
                    Scope    = $scope
                    Location = $k
                    Name     = [string]$x.Name
                    Command  = [string]$x.Value
                    Type     = "Registry"
                    Enabled  = "Yes"
                }
            }
        }
    }
}
$folders = @(
    @{Scope="Current User"; Path=[Environment]::GetFolderPath("Startup")},
    @{Scope="All Users";    Path="$env:ProgramData\Microsoft\Windows\Start Menu\Programs\StartUp"}
)
foreach($f in $folders){
    if (Test-Path $f.Path){
        Get-ChildItem -Force -ErrorAction SilentlyContinue $f.Path | ForEach-Object {
            $items += [pscustomobject]@{
                Scope    = $f.Scope
                Location = $f.Path
                Name     = [string]$_.Name
                Command  = [string]$_.FullName
                Type     = "Startup Folder"
                Enabled  = "Yes"
            }
        }
    }
}
$items | ConvertTo-Json -Depth 4
''', 60)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def disable_startup(row: dict):
    digest = hashlib.sha1(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    backup = STARTUP_BACKUP_DIR / f"startup_{datetime.now():%Y%m%d_%H%M%S_%f}_{digest}.json"
    backup.write_text(json.dumps(row, indent=2), encoding="utf-8")
    if row.get("Type") == "Registry":
        script = f'Remove-ItemProperty -Path "{row.get("Location")}" -Name "{row.get("Name")}" -ErrorAction Stop'
    else:
        script = f'Remove-Item -LiteralPath "{row.get("Command")}" -Force -ErrorAction Stop'
    res = ps(script, 20)
    ok = res.returncode == 0
    log(f"Remove startup {row.get('Name')}: ok={ok}; backup={backup}")
    return ok, str(backup)


def enable_startup(row: dict):
    return True, "Already enabled"


def get_installed_apps() -> list:
    script = r'''
$items = @()
$roots = @(
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
)
foreach($r in $roots){
    Get-ItemProperty $r -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName } | ForEach-Object {
        $items += [pscustomobject]@{
            Name            = [string]$_.DisplayName
            Version         = [string]$_.DisplayVersion
            Publisher       = [string]$_.Publisher
            InstallLocation = [string]$_.InstallLocation
            UninstallString = [string]$_.UninstallString
            Type            = 'Win32'
            Scope           = if ($r -like 'HKCU:*') { 'Current User' } else { 'All Users' }
        }
    }
}
Get-AppxPackage -ErrorAction SilentlyContinue | ForEach-Object {
    $items += [pscustomobject]@{
        Name            = [string]$_.Name
        Version         = [string]$_.Version
        Publisher       = [string]$_.Publisher
        InstallLocation = [string]$_.InstallLocation
        UninstallString = ''
        Type            = 'AppX'
        Scope           = 'Current User'
    }
}
$items | Sort-Object Name | ConvertTo-Json -Depth 5
'''
    data = ps_json(script, 120)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def get_network_adapters() -> list:
    data = ps_json(r'''
Get-NetAdapter -ErrorAction SilentlyContinue | ForEach-Object {
    [pscustomobject]@{
        Name                 = [string]$_.Name
        InterfaceDescription = [string]$_.InterfaceDescription
        Status               = [string]$_.Status
        LinkSpeed            = [string]$_.LinkSpeed
        MacAddress           = [string]$_.MacAddress
        MediaType            = [string]$_.MediaType
    }
} | ConvertTo-Json -Depth 4
''', 45)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def get_tcp_connections() -> list:
    data = ps_json(r'''
Get-NetTCPConnection -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Established' } | ForEach-Object {
    $name = ""
    try { $name = (Get-Process -Id $_.OwningProcess -ErrorAction Stop).ProcessName } catch {}
    [pscustomobject]@{
        LocalAddress  = [string]$_.LocalAddress
        LocalPort     = [int]$_.LocalPort
        RemoteAddress = [string]$_.RemoteAddress
        RemotePort    = [int]$_.RemotePort
        State         = [string]$_.State
        PID           = [int]$_.OwningProcess
        Process       = [string]$name
    }
} | ConvertTo-Json -Depth 4
''', 60)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def cleanup_temp():
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
    log(f"TEMP cleanup: deleted={deleted}, skipped={skipped}")
    return deleted, skipped


def flush_dns() -> bool:
    r = run_cmd(["ipconfig.exe", "/flushdns"], 15)
    ok = r.returncode == 0
    log(f"DNS flush: ok={ok}")
    return ok


def refresh_explorer() -> bool:
    r = ps("Get-Process explorer -ErrorAction SilentlyContinue | Stop-Process -Force; Start-Process explorer.exe", 20)
    return r.returncode == 0


def empty_recycle_bin() -> bool:
    r = ps("Clear-RecycleBin -Force -ErrorAction SilentlyContinue", 30)
    return r.returncode == 0


def component_cleanup():
    r = run_cmd(["DISM.exe", "/Online", "/Cleanup-Image", "/StartComponentCleanup"], 600)
    return r.returncode == 0, (r.stdout or r.stderr)[-2500:]


def scheduled_optimization():
    log("Scheduled background optimizer started")
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
                log(f"Scheduled sleep {pname} PID={pid}: ok={ok} {detail}")
    log("Scheduled background optimizer completed")

# ── 8. REUSABLE FILTERABLE TABLE COMPONENT ────────────────────────────────────
class FilterableTable(ctk.CTkFrame if HAS_CTK else tk.Frame):
    def __init__(self, master, columns, widths=None, default_sort=None,
                 category_field=None, category_label="Category", **kwargs):
        if HAS_CTK:
            super().__init__(master, fg_color="#151922", corner_radius=12, **kwargs)
        else:
            super().__init__(master, bg="#151922", **kwargs)

        self.columns = list(columns)
        self.widths = widths or [150] * len(columns)
        self.default_sort = default_sort or self.columns[0]
        self.sort_column = self.default_sort
        self.sort_reverse = False
        self.category_field = category_field
        self.category_label = category_label
        self.data = []
        self.filtered = []
        self.visible = {c: True for c in self.columns}

        # Top Bar
        top = ctk.CTkFrame(self, fg_color="transparent") if HAS_CTK else tk.Frame(self, bg="#151922")
        top.pack(fill="x", padx=10, pady=(10, 6))
        top.grid_columnconfigure(1, weight=1)

        label_cls = ctk.CTkLabel if HAS_CTK else tk.Label
        entry_cls = ctk.CTkEntry if HAS_CTK else tk.Entry
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button

        label_cls(top, text="Search").grid(row=0, column=0, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filters())
        entry_cls(top, textvariable=self.search_var, width=200 if HAS_CTK else 25).grid(row=0, column=1, sticky="ew", padx=4)

        self.column_var = tk.StringVar(value="All Columns")
        if HAS_CTK:
            self.column_box = ctk.CTkComboBox(
                top, values=["All Columns"] + self.columns,
                variable=self.column_var, width=140, state="readonly",
                command=lambda *_: self.apply_filters()
            )
        else:
            self.column_box = ttk.Combobox(top, values=["All Columns"] + self.columns, textvariable=self.column_var, state="readonly", width=15)
            self.column_box.bind("<<ComboboxSelected>>", lambda *_: self.apply_filters())
        self.column_box.grid(row=0, column=2, padx=4)

        self.operator_var = tk.StringVar(value="Contains")
        ops = ["Contains", "Equals", "Starts With", "Ends With", ">", ">=", "<", "<="]
        if HAS_CTK:
            self.operator_box = ctk.CTkComboBox(
                top, values=ops, variable=self.operator_var, width=115, state="readonly",
                command=lambda *_: self.apply_filters()
            )
        else:
            self.operator_box = ttk.Combobox(top, values=ops, textvariable=self.operator_var, state="readonly", width=12)
            self.operator_box.bind("<<ComboboxSelected>>", lambda *_: self.apply_filters())
        self.operator_box.grid(row=0, column=3, padx=4)

        self.value_var = tk.StringVar()
        self.value_var.trace_add("write", lambda *_: self.apply_filters())
        entry_cls(top, textvariable=self.value_var, width=120 if HAS_CTK else 15).grid(row=0, column=4, padx=4)

        self.category_box = None
        self.category_var = tk.StringVar(value="All")
        if category_field:
            if HAS_CTK:
                self.category_box = ctk.CTkComboBox(
                    top, values=["All"], variable=self.category_var,
                    width=140, state="readonly", command=lambda *_: self.apply_filters()
                )
            else:
                self.category_box = ttk.Combobox(top, values=["All"], textvariable=self.category_var, state="readonly", width=15)
                self.category_box.bind("<<ComboboxSelected>>", lambda *_: self.apply_filters())
            self.category_box.grid(row=0, column=5, padx=4)

        btn_cls(top, text="Clear", width=60 if HAS_CTK else 8, command=self.clear_filters).grid(row=0, column=6, padx=4)
        btn_cls(top, text="Columns", width=70 if HAS_CTK else 10, command=self.column_menu).grid(row=0, column=7, padx=4)
        btn_cls(top, text="Copy", width=55 if HAS_CTK else 8, command=self.copy_selected).grid(row=0, column=8, padx=4)
        btn_cls(top, text="CSV", width=55 if HAS_CTK else 8, command=self.export_csv).grid(row=0, column=9, padx=(4, 0))

        # Body
        body = ctk.CTkFrame(self, fg_color="transparent") if HAS_CTK else tk.Frame(self, bg="#151922")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "OptimusPrime.Treeview", background="#171a21", fieldbackground="#171a21",
            foreground="#eef2f7", rowheight=28, borderwidth=0, font=("Segoe UI", 9)
        )
        style.map(
            "OptimusPrime.Treeview", background=[("selected", "#1d4ed8")],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "OptimusPrime.Treeview.Heading", background="#222733",
            foreground="#b7c2d4", relief="flat", font=("Segoe UI", 9, "bold")
        )

        self.tree = ttk.Treeview(body, columns=self.columns, show="headings",
                                 selectmode="extended", style="OptimusPrime.Treeview")
        for col, width in zip(self.columns, self.widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=width, minwidth=50, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        ys = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        xs = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")

        self.info = label_cls(self, text="0 rows")
        if HAS_CTK:
            self.info.configure(text_color="#7d8899")
        self.info.pack(anchor="w", padx=12, pady=(0, 6))

    def set_data(self, rows):
        self.data = list(rows or [])
        if self.category_field and self.category_box:
            vals = sorted({norm(r.get(self.category_field)) for r in self.data if norm(r.get(self.category_field))})
            options = ["All"] + vals
            cur = self.category_var.get()
            if HAS_CTK:
                self.category_box.configure(values=options)
            else:
                self.category_box["values"] = options
            self.category_var.set(cur if cur in options else "All")
        self.apply_filters()

    def _matches(self, row, col, op, target):
        text = (" | ".join(norm(row.get(c)) for c in self.columns)
                if col == "All Columns" else norm(row.get(col)))
        a, b = text.lower(), norm(target).lower()
        if op == "Contains": return b in a
        if op == "Equals": return a == b
        if op == "Starts With": return a.startswith(b)
        if op == "Ends With": return a.endswith(b)
        try:
            na = float(text.replace(",", "").replace("%", ""))
            nb = float(norm(target).replace(",", "").replace("%", ""))
        except Exception:
            na, nb = a, b
        return {">": na > nb, ">=": na >= nb, "<": na < nb, "<=": na <= nb}.get(op, False)

    def apply_filters(self):
        search = self.search_var.get().strip().lower()
        col, op, val = self.column_var.get(), self.operator_var.get(), self.value_var.get().strip()
        category = self.category_var.get()
        rows = []
        for row in self.data:
            if self.category_field and category != "All" and norm(row.get(self.category_field)) != category:
                continue
            if search:
                all_text = " | ".join(norm(row.get(c)) for c in self.columns).lower()
                if search not in all_text:
                    continue
            if val and not self._matches(row, col, op, val):
                continue
            rows.append(row)

        def sort_key(r):
            v = norm(r.get(self.sort_column))
            try:
                return (0, float(v.replace(",", "").replace("%", "").strip()))
            except Exception:
                return (1, v.lower())

        rows.sort(key=sort_key, reverse=self.sort_reverse)
        self.filtered = rows
        self.render()

    def render(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        display = [c for c in self.columns if self.visible.get(c, True)]
        self.tree["displaycolumns"] = display
        for col, width in zip(self.columns, self.widths):
            self.tree.column(col, width=width if self.visible.get(col, True) else 0)
        for idx, row in enumerate(self.filtered):
            self.tree.insert("", "end", iid=str(idx), values=[norm(row.get(c)) for c in self.columns])
        arrow = "▼" if self.sort_reverse else "▲"
        self.info.configure(text=f"{len(self.filtered):,} / {len(self.data):,} rows   •   Sorted by {self.sort_column} {arrow}")

    def sort_by(self, col):
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column, self.sort_reverse = col, False
        self.apply_filters()

    def clear_filters(self):
        self.search_var.set("")
        self.column_var.set("All Columns")
        self.operator_var.set("Contains")
        self.value_var.set("")
        self.category_var.set("All")
        self.apply_filters()

    def selected_rows(self):
        output = []
        for iid in self.tree.selection():
            try:
                output.append(self.filtered[int(iid)])
            except Exception:
                pass
        return output

    def column_menu(self):
        popup = (ctk.CTkToplevel(self) if HAS_CTK else tk.Toplevel(self))
        popup.title("Column Visibility")
        popup.geometry("320x460")
        popup.transient(self.winfo_toplevel())
        (ctk.CTkLabel if HAS_CTK else tk.Label)(popup, text="Select Visible Columns", font=("Segoe UI", 13, "bold")).pack(pady=12)
        body = (ctk.CTkScrollableFrame(popup) if HAS_CTK else tk.Frame(popup))
        body.pack(fill="both", expand=True, padx=12, pady=5)
        vars_map = {}
        chk_cls = ctk.CTkCheckBox if HAS_CTK else tk.Checkbutton
        for col in self.columns:
            var = tk.BooleanVar(value=self.visible.get(col, True))
            vars_map[col] = var
            chk_cls(body, text=col, variable=var).pack(anchor="w", pady=4)

        def apply():
            self.visible.update({c: v.get() for c, v in vars_map.items()})
            if not any(self.visible.values()):
                self.visible[self.columns[0]] = True
            self.render()
            popup.destroy()

        (ctk.CTkButton if HAS_CTK else tk.Button)(popup, text="Apply", command=apply).pack(pady=12)

    def copy_selected(self):
        rows = self.selected_rows()
        if not rows:
            return
        text = "\n".join("\t".join(norm(r.get(c)) for c in self.columns) for r in rows)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.info.configure(text=f"Copied {len(rows)} selected row(s)")

    def export_csv(self):
        path = filedialog.asksaveasfilename(
            title="Export Current Filtered View", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=self.columns)
                writer.writeheader()
                writer.writerows(self.filtered)
            self.info.configure(text=f"Exported {len(self.filtered):,} rows")
            log(f"CSV exported: {path}")
        except Exception as exc:
            messagebox.showerror("Export CSV", str(exc))

# ── 9. MAIN GUI APPLICATION CLASS ─────────────────────────────────────────────
class OptimusPrimeStandaloneApp(ctk.CTk if HAS_CTK else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"{APP_NAME} — {APP_SUBTITLE}")
        self.geometry("1580x960")
        self.minsize(1180, 720)
        if HAS_CTK:
            self.configure(fg_color="#0b0f14")

        self.processes = []
        self.tasks = []
        self.services = []
        self.startups = []
        self.apps = []
        self.adapters = []
        self.connections = []
        self.drives = []
        self.system = {}
        self.memory = {}
        self.auto_sleep_started = {}
        self.performance_history = []
        self._is_refreshing = False

        self._build_shell()
        self._build_pages()

        saved_page = CONFIG.get("last_page", "Dashboard")
        if saved_page not in self.pages:
            saved_page = "Dashboard"
        self.select_page(saved_page)

        self.after(300, self.refresh_all)
        self.after(1000, self.auto_sleep_tick)
        self.after(1500, self.update_performance_loop)

    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = (ctk.CTkFrame(self, width=240, corner_radius=0, fg_color="#11151c")
                        if HAS_CTK else tk.Frame(self, width=240, bg="#11151c"))
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        lbl_cls = ctk.CTkLabel if HAS_CTK else tk.Label
        lbl_cls(self.sidebar, text="⚡ OPTIMUSPRIME", font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=18, pady=(20, 0))
        lbl_cls(self.sidebar, text="ULTIMATE SYSTEM CONTROL", font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=18, pady=(0, 16))

        pages = [
            "Dashboard", "Processes", "App Sleep", "Scheduled Tasks", "Services",
            "Startup", "Applications", "Network", "Performance", "Storage",
            "Maintenance", "System", "Reports", "Log"
        ]
        self.nav_buttons = {}
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        for name in pages:
            b = (ctk.CTkButton(self.sidebar, text=name, anchor="w", height=36, corner_radius=8,
                               fg_color="transparent", hover_color="#1d2330", font=("Segoe UI", 11),
                               command=lambda n=name: self.select_page(n))
                 if HAS_CTK else tk.Button(self.sidebar, text=name, anchor="w",
                                           bg="#11151c", fg="#ffffff", command=lambda n=name: self.select_page(n)))
            b.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = b

        footer = (ctk.CTkFrame(self.sidebar, fg_color="transparent") if HAS_CTK else tk.Frame(self.sidebar, bg="#11151c"))
        footer.pack(side="bottom", fill="x", padx=12, pady=14)

        admin = is_admin()
        self.admin_label = lbl_cls(
            footer, text="ADMINISTRATOR" if admin else "STANDARD USER",
            font=("Segoe UI", 10, "bold")
        )
        if HAS_CTK:
            self.admin_label.configure(text_color="#57d6a0" if admin else "#ffbd63")
        self.admin_label.pack(anchor="w")

        self.sidebar_stats = lbl_cls(footer, text="Initializing…", justify="left")
        if HAS_CTK:
            self.sidebar_stats.configure(text_color="#7d8899")
        self.sidebar_stats.pack(anchor="w", pady=(4, 0))

        if not admin:
            (ctk.CTkButton(footer, text="Restart Elevated", height=32, command=self.restart_elevated)
             if HAS_CTK else tk.Button(footer, text="Restart Elevated", command=self.restart_elevated)).pack(fill="x", pady=(8, 0))

        main = (ctk.CTkFrame(self, corner_radius=0, fg_color="#0b0f14") if HAS_CTK else tk.Frame(self, bg="#0b0f14"))
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)

        top = (ctk.CTkFrame(main, height=64, corner_radius=0, fg_color="#0b0f14") if HAS_CTK else tk.Frame(main, bg="#0b0f14"))
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        self.page_title = lbl_cls(top, text=APP_NAME, font=("Segoe UI", 20, "bold"))
        self.page_title.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="w")
        self.global_status = lbl_cls(top, text="Ready", font=("Segoe UI", 10))
        if HAS_CTK:
            self.global_status.configure(text_color="#7d8899")
        self.global_status.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        self.badge = lbl_cls(top, text="ADMIN" if admin else "STANDARD", font=("Segoe UI", 10, "bold"))
        if HAS_CTK:
            self.badge.configure(text_color="#57d6a0" if admin else "#ffbd63")
        self.badge.grid(row=0, column=2, padx=12)

        (ctk.CTkButton(top, text="⟳ Refresh", width=90, height=32, command=self.refresh_all)
         if HAS_CTK else tk.Button(top, text="Refresh", command=self.refresh_all)).grid(row=0, column=3, rowspan=2, padx=12)

        self.content = (ctk.CTkFrame(main, fg_color="transparent", corner_radius=0)
                        if HAS_CTK else tk.Frame(main, bg="#0b0f14"))
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.pages = {}

    def select_page(self, name):
        if name in self.pages:
            self.page_title.configure(text=name)
            self.pages[name].tkraise()
            for n, b in self.nav_buttons.items():
                if HAS_CTK:
                    b.configure(fg_color="#1d4ed8" if n == name else "transparent")
            CONFIG["last_page"] = name
            save_config()

    def set_status(self, text):
        self.global_status.configure(text=str(text))

    def new_page(self, name):
        p = (ctk.CTkFrame(self.content, fg_color="transparent")
             if HAS_CTK else tk.Frame(self.content, bg="#0b0f14"))
        p.grid(row=0, column=0, sticky="nsew")
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.pages[name] = p
        return p

    def _card(self, parent, key, title, col):
        frame = (ctk.CTkFrame(parent, corner_radius=12, fg_color="#151922")
                 if HAS_CTK else tk.Frame(parent, bg="#151922"))
        frame.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
        lbl_cls = ctk.CTkLabel if HAS_CTK else tk.Label
        l1 = lbl_cls(frame, text=title, font=("Segoe UI", 9, "bold"))
        if HAS_CTK: l1.configure(text_color="#7d8899")
        l1.pack(anchor="w", padx=14, pady=(10, 0))
        var = tk.StringVar(value="—")
        lbl_cls(frame, textvariable=var, font=("Segoe UI", 16, "bold")).pack(anchor="w", padx=14, pady=(4, 12))
        self.card_vars[key] = var

    def _build_pages(self):
        self._build_dashboard()
        self._build_processes()
        self._build_app_sleep()
        self._build_tasks()
        self._build_services()
        self._build_startup()
        self._build_apps()
        self._build_network()
        self._build_performance()
        self._build_storage()
        self._build_maintenance()
        self._build_system()
        self._build_reports()
        self._build_log()

    # 1. Dashboard
    def _build_dashboard(self):
        p = self.new_page("Dashboard")
        p.grid_rowconfigure(2, weight=1)
        p.grid_columnconfigure(0, weight=1)

        head = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(8, 6))
        (ctk.CTkLabel if HAS_CTK else tk.Label)(head, text="System Health & Live Monitoring", font=("Segoe UI", 15, "bold")).pack(side="left")
        (ctk.CTkButton(head, text="⚡ Smart Optimize", width=140, height=34, command=self.smart_optimize)
         if HAS_CTK else tk.Button(head, text="Smart Optimize", command=self.smart_optimize)).pack(side="right")

        self.card_vars = {}
        cards = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        cards.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        for i in range(5): cards.grid_columnconfigure(i, weight=1)
        for i, (k, t) in enumerate([("RAM", "Physical Memory"), ("PROC", "Active Processes"), ("TOP", "Top Memory User"), ("DISK", "Drive C: Free"), ("TASK", "Optimizer Task")]):
            self._card(cards, k, t, i)

        body = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = (ctk.CTkFrame(body, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(body, bg="#151922"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        (ctk.CTkLabel if HAS_CTK else tk.Label)(left, text="Top Memory Consumers", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        self.dashboard_table = FilterableTable(left, ["Name", "PID", "RAM_MB", "CPU_s", "Owner"], [220, 70, 95, 85, 240], default_sort="RAM_MB")
        self.dashboard_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        right = (ctk.CTkFrame(body, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(body, bg="#151922"))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        (ctk.CTkLabel if HAS_CTK else tk.Label)(right, text="Quick Management Center", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        for text, cmd in [
            ("◌ App Sleep Management", lambda: self.select_page("App Sleep")),
            ("☷ Scheduled Tasks Control", lambda: self.select_page("Scheduled Tasks")),
            ("⚙ Windows Services Manager", lambda: self.select_page("Services")),
            ("↥ Startup Applications", lambda: self.select_page("Startup")),
            ("▣ Installed Applications", lambda: self.select_page("Applications")),
            ("▤ Export Full JSON Audit", self.export_audit),
        ]:
            (ctk.CTkButton(right, text=text, height=38, fg_color="#1e2430", anchor="w", command=cmd)
             if HAS_CTK else tk.Button(right, text=text, anchor="w", command=cmd)).pack(fill="x", padx=14, pady=4)

        self.dashboard_note = (ctk.CTkLabel(right, text="", justify="left", wraplength=360)
                               if HAS_CTK else tk.Label(right, text="", justify="left"))
        self.dashboard_note.pack(anchor="w", padx=14, pady=14)

    # 2. Processes
    def _build_processes(self):
        p = self.new_page("Processes")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        for text, cmd in [("Sleep", self.sleep_selected), ("Wake", self.wake_selected), ("Trim Working Set", self.trim_selected), ("Terminate", self.terminate_selected)]:
            btn_cls(bar, text=text, command=cmd).pack(side="left", padx=3)
        btn_cls(bar, text="END ALL FILTERED USER PROCESSES", command=self.end_filtered_user).pack(side="right")

        self.process_table = FilterableTable(
            p, ["PID", "Name", "RAM_MB", "CPU_s", "Owner", "SessionId", "Path", "CommandLine"],
            [70, 180, 95, 85, 200, 80, 500, 600], default_sort="RAM_MB"
        )
        self.process_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def sleep_selected(self):
        rows = self.process_table.selected_rows()
        if not rows: return messagebox.showinfo("Sleep", "Select process(es).")
        for r in rows:
            pname = name_key(r.get("Name"))
            pid = int(r.get("PID", 0) or 0)
            if pname in PROTECTED_PROCESSES: continue
            suspend_process(pid)
        self.refresh_processes()

    def wake_selected(self):
        rows = self.process_table.selected_rows()
        if not rows: return messagebox.showinfo("Wake", "Select process(es).")
        for r in rows:
            resume_process(int(r.get("PID", 0) or 0))
        self.refresh_processes()

    def trim_selected(self):
        rows = self.process_table.selected_rows()
        if not rows: return messagebox.showinfo("Trim", "Select process(es).")
        done = sum(1 for r in rows if name_key(r.get("Name")) not in PROTECTED_PROCESSES and trim_working_set(int(r.get("PID", 0) or 0))[0])
        self.set_status(f"Trimmed {done}/{len(rows)} processes")
        self.refresh_processes()

    def terminate_selected(self):
        rows = [r for r in self.process_table.selected_rows() if name_key(r.get("Name")) not in PROTECTED_PROCESSES]
        if not rows: return messagebox.showwarning("Terminate", "No eligible non-protected process selected.")
        if not messagebox.askyesno("Confirm", f"Terminate {len(rows)} process(es)?"): return
        n, _ = terminate_pids([int(r["PID"]) for r in rows])
        self.set_status(f"Terminated {n}/{len(rows)}"); self.refresh_all()

    def end_filtered_user(self):
        if not is_admin(): return messagebox.showwarning("Administrator", "Please elevate to terminate user processes.")
        me = name_key(os.environ.get("USERNAME"))
        rows = [r for r in self.process_table.filtered if int(r.get("PID", 0) or 0) > 4 and name_key(r.get("Name")) not in PROTECTED_PROCESSES and (not norm(r.get("Owner")).lower() or norm(r.get("Owner")).lower().endswith("\\" + me))]
        if not rows: return messagebox.showinfo("Notice", "No eligible user processes in current filter.")
        if not messagebox.askyesno("DANGER", f"Terminate {len(rows)} filtered processes?"): return
        n, _ = terminate_pids([int(r["PID"]) for r in rows])
        self.set_status(f"Mass terminated {n}/{len(rows)}"); self.refresh_all()

    # 3. App Sleep
    def _build_app_sleep(self):
        p = self.new_page("App Sleep")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        rule = (ctk.CTkFrame(p, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(p, bg="#151922"))
        rule.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        rule.grid_columnconfigure(1, weight=1)

        self.sleep_enabled_var = tk.BooleanVar(value=bool(CONFIG.get("auto_sleep_enabled")))
        self.sleep_minutes_var = tk.StringVar(value=str(CONFIG.get("auto_sleep_after_minutes", 10)))
        self.sleep_rule_var = tk.StringVar(value=", ".join(CONFIG.get("auto_sleep_processes", ["msedge.exe"])))
        self.scheduled_sleep_var = tk.BooleanVar(value=bool(CONFIG.get("scheduled_auto_sleep")))

        chk_cls = ctk.CTkCheckBox if HAS_CTK else tk.Checkbutton
        lbl_cls = ctk.CTkLabel if HAS_CTK else tk.Label
        ent_cls = ctk.CTkEntry if HAS_CTK else tk.Entry

        chk_cls(rule, text="Enable automatic sleep for minimized matching apps", variable=self.sleep_enabled_var, command=self.save_sleep_settings).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))
        lbl_cls(rule, text="Minutes Minimized").grid(row=1, column=0, sticky="w", padx=14, pady=4)
        ent_cls(rule, textvariable=self.sleep_minutes_var, width=80 if HAS_CTK else 10).grid(row=1, column=1, sticky="w", padx=8, pady=4)
        lbl_cls(rule, text="Target Process Rules").grid(row=2, column=0, sticky="w", padx=14, pady=4)
        ent_cls(rule, textvariable=self.sleep_rule_var).grid(row=2, column=1, sticky="ew", padx=8, pady=4)
        chk_cls(rule, text="Integrate these rules into Scheduled Background Optimizer", variable=self.scheduled_sleep_var, command=self.save_sleep_settings).grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 12))

        btns = (ctk.CTkFrame(rule, fg_color="transparent") if HAS_CTK else tk.Frame(rule, bg="#151922"))
        btns.grid(row=1, column=2, rowspan=2, padx=14, sticky="e")
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        btn_cls(btns, text="Select Processes", command=self.open_process_picker).pack(side="top", pady=3)
        btn_cls(btns, text="Find Minimized", command=self.find_sleep_candidates).pack(side="top", pady=3)
        btn_cls(btns, text="Save Rules", command=self.save_sleep_settings).pack(side="top", pady=3)

        self.sleep_table = FilterableTable(p, ["PID", "Name", "RAM_MB", "Minimized", "Path"], [80, 200, 100, 100, 800], default_sort="RAM_MB")
        self.sleep_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))

        bottom = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        bottom.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        btn_cls(bottom, text="Sleep Selected", command=self.sleep_sleep_rows).pack(side="left", padx=3)
        btn_cls(bottom, text="Wake Selected", command=self.wake_sleep_rows).pack(side="left", padx=3)

    def save_sleep_settings(self):
        try: m = max(1, int(self.sleep_minutes_var.get()))
        except Exception: m = 10; self.sleep_minutes_var.set("10")
        CONFIG["auto_sleep_enabled"] = bool(self.sleep_enabled_var.get())
        CONFIG["auto_sleep_after_minutes"] = m
        CONFIG["auto_sleep_processes"] = [x.strip() for x in self.sleep_rule_var.get().split(",") if x.strip()]
        CONFIG["scheduled_auto_sleep"] = bool(self.scheduled_sleep_var.get())
        save_config(); self.set_status("App Sleep settings saved")

    def open_process_picker(self):
        picker = (ctk.CTkToplevel(self) if HAS_CTK else tk.Toplevel(self))
        picker.title("Select Applications & Processes")
        picker.geometry("740x680")
        picker.transient(self)

        top = (ctk.CTkFrame(picker, fg_color="transparent") if HAS_CTK else tk.Frame(picker))
        top.pack(fill="x", padx=12, pady=10)
        search = tk.StringVar()
        (ctk.CTkEntry(top, textvariable=search, placeholder_text="Search process…")
         if HAS_CTK else tk.Entry(top, textvariable=search)).pack(side="left", fill="x", expand=True)

        list_frame = (ctk.CTkScrollableFrame(picker) if HAS_CTK else tk.Frame(picker))
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        rows = self.processes[:]
        selected = {name_key(x) for x in CONFIG.get("auto_sleep_processes", [])}

        def render():
            for w in list_frame.winfo_children(): w.destroy()
            q = search.get().lower().strip()
            seen = set()
            for r in rows:
                pname = name_key(r.get("Name"))
                path = norm(r.get("Path"))
                key = (pname, path.lower())
                if key in seen: continue
                seen.add(key)
                text = f"{r.get('Name', '')}   •   {path}"
                if q and q not in text.lower(): continue

                f = (ctk.CTkFrame(list_frame, fg_color="#151922", corner_radius=8) if HAS_CTK else tk.Frame(list_frame, bg="#151922"))
                f.pack(fill="x", pady=3)
                var = tk.BooleanVar(value=pname in selected)

                (ctk.CTkCheckBox(f, text=text, variable=var) if HAS_CTK else tk.Checkbutton(f, text=text, variable=var)).pack(side="left", fill="x", expand=True, padx=6, pady=6)
                def bind(v=var, n=pname):
                    def fn(*_):
                        if v.get(): selected.add(n)
                        else: selected.discard(n)
                    return fn
                var.trace_add("write", bind())
        search.trace_add("write", lambda *_: render()); render()
        (ctk.CTkButton(picker, text="Apply Selection", command=lambda: (self.sleep_rule_var.set(", ".join(sorted(x + ".exe" for x in selected))), self.save_sleep_settings(), picker.destroy()))
         if HAS_CTK else tk.Button(picker, text="Apply Selection", command=picker.destroy)).pack(pady=(0, 12))

    def find_sleep_candidates(self):
        minimized = minimize_pid_set()
        rows = [{"PID": int(r.get("PID", 0) or 0), "Name": r.get("Name"), "RAM_MB": r.get("RAM_MB"), "Minimized": "Yes", "Path": r.get("Path")}
                for r in self.processes if int(r.get("PID", 0) or 0) in minimized and name_key(r.get("Name")) not in PROTECTED_PROCESSES]
        self.sleep_table.set_data(rows)
        self.set_status(f"Found {len(rows)} minimized process candidates")

    def refresh_sleep_table(self):
        minimized = minimize_pid_set()
        rules = {name_key(x) for x in CONFIG.get("auto_sleep_processes", [])}
        rows = [{"PID": int(r.get("PID", 0) or 0), "Name": r.get("Name"), "RAM_MB": r.get("RAM_MB"), "Minimized": "Yes" if int(r.get("PID", 0) or 0) in minimized else "No", "Path": r.get("Path")}
                for r in self.processes if name_key(r.get("Name")) in rules or int(r.get("PID", 0) or 0) in minimized]
        self.sleep_table.set_data(rows)

    def sleep_sleep_rows(self):
        for r in self.sleep_table.selected_rows():
            if name_key(r.get("Name")) not in PROTECTED_PROCESSES:
                suspend_process(int(r.get("PID", 0) or 0))
        self.refresh_processes()

    def wake_sleep_rows(self):
        for r in self.sleep_table.selected_rows():
            resume_process(int(r.get("PID", 0) or 0))
        self.refresh_processes()

    def auto_sleep_tick(self):
        try:
            if CONFIG.get("auto_sleep_enabled"):
                rules = {name_key(x) for x in CONFIG.get("auto_sleep_processes", []) if norm(x)}
                minimized = minimize_pid_set()
                now = time.time()
                minutes = max(1, int(CONFIG.get("auto_sleep_after_minutes", 10)))
                for r in self.processes:
                    pid = int(r.get("PID", 0) or 0)
                    pname = name_key(r.get("Name"))
                    if not pid or pname not in rules or pname in PROTECTED_PROCESSES: continue
                    if pid in minimized:
                        started = self.auto_sleep_started.setdefault(pid, now)
                        if now - started >= minutes * 60:
                            ok, _ = suspend_process(pid)
                            self.auto_sleep_started[pid] = now + 86400 if ok else now
                    else:
                        self.auto_sleep_started.pop(pid, None)
        except Exception:
            pass
        self.after(30000, self.auto_sleep_tick)

    # 4. Scheduled Tasks
    def _build_tasks(self):
        p = self.new_page("Scheduled Tasks")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        self.task_interval = tk.StringVar(value="60")
        (ctk.CTkLabel if HAS_CTK else tk.Label)(bar, text="Interval").pack(side="left")
        if HAS_CTK:
            ctk.CTkComboBox(bar, variable=self.task_interval, values=["15", "30", "60", "120", "360", "720", "1440"], width=85, state="readonly").pack(side="left", padx=6)
        else:
            ttk.Combobox(bar, textvariable=self.task_interval, values=["15", "30", "60", "120", "360", "720", "1440"], width=8, state="readonly").pack(side="left", padx=6)

        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        btn_cls(bar, text="Register Optimizer", command=self.create_optimizer_task_ui).pack(side="left", padx=4)
        btn_cls(bar, text="Enable Filtered", command=lambda: self.bulk_tasks("enable")).pack(side="left", padx=3)
        btn_cls(bar, text="Disable Filtered", command=lambda: self.bulk_tasks("disable")).pack(side="left", padx=3)
        btn_cls(bar, text="Run Filtered", command=lambda: self.bulk_tasks("run")).pack(side="left", padx=3)
        btn_cls(bar, text="Delete Filtered + XML", command=lambda: self.bulk_tasks("delete")).pack(side="left", padx=3)

        self.task_table = FilterableTable(
            p, ["TaskName", "TaskPath", "State", "Author", "RunLevel", "LastRun", "NextRun", "Category", "Scope", "OptimizerOwned", "Actions"],
            [220, 240, 90, 160, 100, 160, 160, 140, 140, 110, 480], default_sort="TaskName", category_field="Category"
        )
        self.task_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def create_optimizer_task_ui(self):
        if not is_admin(): return messagebox.showwarning("Administrator", "Please elevate the application.")
        try: m = max(15, int(self.task_interval.get()))
        except Exception: return messagebox.showerror("Interval", "Invalid interval.")
        CONFIG["scheduled_clean_temp"] = True; CONFIG["scheduled_flush_dns"] = True; save_config()
        try:
            create_optimizer_task(m); self.refresh_tasks()
            messagebox.showinfo("Task Scheduler", f"Created optimizer task every {m} minutes.")
        except Exception as exc: messagebox.showerror("Error", str(exc))

    def bulk_tasks(self, action):
        rows = self.task_table.filtered
        if not rows: return messagebox.showinfo("Tasks", "No tasks in view.")
        target = [r for r in rows if r.get("Category") != "Microsoft" and not norm(r.get("TaskPath")).lower().startswith("\\microsoft\\")]
        if not target: return messagebox.showinfo("Tasks", "No eligible non-Microsoft tasks in view.")
        title = action.title()
        if not messagebox.askyesno(f"Bulk {title}", f"{title} {len(target)} task(s)?"): return
        done = 0
        for r in target:
            full = full_task_name(r.get("TaskPath"), r.get("TaskName"))
            if action == "delete": ok, _ = delete_task(full)
            elif action == "run": ok = task_run(full)
            else: ok = task_enable(full, action == "enable")
            done += int(ok)
        self.set_status(f"Tasks {title}: {done}/{len(target)}"); self.refresh_tasks()

    # 5. Services
    def _build_services(self):
        p = self.new_page("Services")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        for label, act in [("Start", "start"), ("Stop", "stop"), ("Restart", "restart"), ("Automatic", "automatic"), ("Delayed", "delayed"), ("Manual", "manual"), ("Disabled", "disabled")]:
            btn_cls(bar, text=label, width=70 if HAS_CTK else 8, command=lambda a=act: self.bulk_services(a)).pack(side="right", padx=2)

        self.service_table = FilterableTable(
            p, ["Name", "DisplayName", "State", "StartMode", "StartName", "ProcessId", "Category", "Path", "Description"],
            [160, 240, 90, 100, 170, 80, 150, 520, 380], default_sort="DisplayName", category_field="Category"
        )
        self.service_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def bulk_services(self, action):
        rows = self.service_table.filtered
        eligible = [r for r in rows if r.get("Name") not in PROTECTED_SERVICE_NAMES and r.get("Category") != "Security"]
        if not eligible: return messagebox.showwarning("Services", "No eligible non-protected services in view.")
        if not messagebox.askyesno("Service Change", f"Apply '{action}' to {len(eligible)} service(s)?"): return
        done = sum(1 for r in eligible if service_action(r.get("Name"), action)[0])
        self.set_status(f"Services {action}: {done}/{len(eligible)}"); self.refresh_services()

    # 6. Startup
    def _build_startup(self):
        p = self.new_page("Startup")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        for text, act in [("Enable Filtered", "enable"), ("Disable Filtered", "disable"), ("Delete Filtered", "delete")]:
            btn_cls(bar, text=text, command=lambda a=act: self.bulk_startup(a)).pack(side="left", padx=3)

        self.startup_table = FilterableTable(
            p, ["Scope", "Location", "Name", "Command", "Type", "Enabled"],
            [120, 320, 200, 780, 140, 90], default_sort="Name", category_field="Type"
        )
        self.startup_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def bulk_startup(self, action):
        rows = self.startup_table.filtered
        if not rows: return messagebox.showinfo("Startup", "No rows in view.")
        if not messagebox.askyesno("Confirm", f"{action.title()} {len(rows)} item(s)?"): return
        done = sum(1 for r in rows if (enable_startup(r)[0] if action == "enable" else disable_startup(r)[0]))
        self.set_status(f"Startup {action}: {done}/{len(rows)}"); self.refresh_startup()

    # 7. Applications
    def _build_apps(self):
        p = self.new_page("Applications")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        btn_cls(bar, text="Refresh Installed Apps", command=self.refresh_apps).pack(side="left")
        btn_cls(bar, text="Open Install Location", command=self.open_app_location).pack(side="left", padx=5)
        btn_cls(bar, text="Open Windows Apps Settings", command=self.open_app_settings).pack(side="left", padx=5)

        self.app_table = FilterableTable(
            p, ["Name", "Version", "Publisher", "InstallLocation", "UninstallString", "Type", "Scope"],
            [240, 120, 200, 520, 520, 90, 120], default_sort="Name", category_field="Type"
        )
        self.app_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def open_app_location(self):
        rows = self.app_table.selected_rows()
        if not rows: return messagebox.showinfo("Applications", "Select an app.")
        path = norm(rows[0].get("InstallLocation"))
        if path and Path(path).exists(): os.startfile(path)
        else: messagebox.showwarning("Applications", "Location unavailable.")

    def open_app_settings(self):
        run_cmd(["explorer.exe", "ms-settings:appsfeatures"], 10)

    # 8. Network
    def _build_network(self):
        p = self.new_page("Network")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        (ctk.CTkButton if HAS_CTK else tk.Button)(top, text="Refresh Network", command=self.refresh_network).pack(side="left")

        body = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(0, weight=1)

        left = (ctk.CTkFrame(body, fg_color="transparent") if HAS_CTK else tk.Frame(body, bg="#0b0f14"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right = (ctk.CTkFrame(body, fg_color="transparent") if HAS_CTK else tk.Frame(body, bg="#0b0f14"))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.adapter_table = FilterableTable(left, ["Name", "InterfaceDescription", "Status", "LinkSpeed", "MacAddress", "MediaType"], [130, 280, 90, 110, 140, 120], default_sort="Name", category_field="Status")
        self.adapter_table.pack(fill="both", expand=True)

        self.tcp_table = FilterableTable(right, ["LocalAddress", "LocalPort", "RemoteAddress", "RemotePort", "State", "PID", "Process"], [140, 75, 180, 85, 95, 75, 170], default_sort="Process", category_field="State")
        self.tcp_table.pack(fill="both", expand=True)

    # 9. Performance
    def _build_performance(self):
        p = self.new_page("Performance")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)

        self.perf_labels = {}
        for key in ("CPU", "RAM", "NETWORK", "DISK"):
            var = tk.StringVar(value="—")
            self.perf_labels[key] = var
            f = (ctk.CTkFrame(top, corner_radius=10, fg_color="#151922") if HAS_CTK else tk.Frame(top, bg="#151922"))
            f.pack(side="left", fill="x", expand=True, padx=4)
            (ctk.CTkLabel if HAS_CTK else tk.Label)(f, text=key, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 0))
            (ctk.CTkLabel if HAS_CTK else tk.Label)(f, textvariable=var, font=("Segoe UI", 15, "bold")).pack(anchor="w", padx=12, pady=(2, 8))

        history = (ctk.CTkFrame(p, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(p, bg="#151922"))
        history.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.perf_table = FilterableTable(history, ["Time", "CPU_%", "RAM_%", "NetRx_KB", "NetTx_KB"], [160, 90, 90, 130, 130], default_sort="Time")
        self.perf_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def update_performance_loop(self):
        def worker():
            sample = get_performance_sample()
            now = datetime.now().strftime("%H:%M:%S")
            self.after(0, lambda: self._apply_perf(sample, now))
        threading.Thread(target=worker, daemon=True).start()
        self.after(5000, self.update_performance_loop)

    def _apply_perf(self, sample, now):
        c = sample.get("CPU", 0); r = sample.get("RAM", 0); rx = sample.get("Rx", 0); tx = sample.get("Tx", 0)
        self.perf_labels["CPU"].set(f"{c} %")
        self.perf_labels["RAM"].set(f"{r} %")
        self.perf_labels["NETWORK"].set(f"Rx {rx} KB / Tx {tx} KB")
        self.perf_labels["DISK"].set("Active")
        self.performance_history.append({"Time": now, "CPU_%": c, "RAM_%": r, "NetRx_KB": rx, "NetTx_KB": tx})
        self.performance_history = self.performance_history[-120:]
        self.perf_table.set_data(list(reversed(self.performance_history)))

    # 10. Storage
    def _build_storage(self):
        p = self.new_page("Storage")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        btn_cls(top, text="Refresh Storage", command=self.refresh_drives).pack(side="left")
        btn_cls(top, text="Clean TEMP", command=lambda: self.run_storage_cleanup("temp")).pack(side="left", padx=5)
        btn_cls(top, text="Empty Recycle Bin", command=lambda: self.run_storage_cleanup("recycle")).pack(side="left", padx=5)
        btn_cls(top, text="DISM Component Cleanup", command=self.run_dism).pack(side="left", padx=5)

        self.storage_table = FilterableTable(p, ["DeviceID", "UsedGB", "FreeGB", "TotalGB", "FileSystem", "VolumeName"], [90, 110, 110, 110, 120, 250], default_sort="FreeGB")
        self.storage_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def run_storage_cleanup(self, which):
        if which == "temp":
            d, s = cleanup_temp(); messagebox.showinfo("TEMP", f"Deleted {d}; skipped {s}")
        else:
            messagebox.showinfo("Recycle Bin", "Purged." if empty_recycle_bin() else "Failed.")
        self.refresh_drives()

    # 11. Maintenance
    def _build_maintenance(self):
        p = self.new_page("Maintenance")
        box = (ctk.CTkFrame(p, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(p, bg="#151922"))
        box.pack(fill="x", padx=18, pady=18)
        (ctk.CTkLabel if HAS_CTK else tk.Label)(box, text="Safe System Maintenance", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        for text, cmd in [("Clean TEMP Cache", cleanup_temp), ("Flush DNS Resolver Cache", flush_dns), ("Restart Windows Explorer Shell", refresh_explorer), ("Empty Recycle Bin", empty_recycle_bin)]:
            btn_cls(box, text=text, width=220 if HAS_CTK else 25, command=lambda f=cmd: self.run_maintenance_action(f)).pack(anchor="w", padx=16, pady=5)

        adv = (ctk.CTkFrame(p, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(p, bg="#151922"))
        adv.pack(fill="x", padx=18, pady=(0, 18))
        (ctk.CTkLabel if HAS_CTK else tk.Label)(adv, text="Advanced DISM Servicing", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        btn_cls(adv, text="RUN DISM COMPONENT CLEANUP", command=self.run_dism).pack(anchor="w", padx=16, pady=12)

    def run_maintenance_action(self, func):
        def work():
            res = func(); self.after(0, lambda: messagebox.showinfo("Maintenance", str(res)))
        threading.Thread(target=work, daemon=True).start()

    def run_dism(self):
        if not messagebox.askyesno("DISM", "Run DISM StartComponentCleanup?"): return
        def work():
            ok, text = component_cleanup()
            self.after(0, lambda: messagebox.showinfo("DISM", ("Completed" if ok else "Error") + "\n\n" + text[-1500:]))
        threading.Thread(target=work, daemon=True).start()

    def smart_optimize(self):
        if not messagebox.askyesno("Smart Optimize", "Run safe optimization?\n\nTEMP + DNS + Explorer restart."): return
        def work():
            cleanup_temp(); flush_dns(); refresh_explorer(); self.after(0, self.refresh_all)
        threading.Thread(target=work, daemon=True).start()

    # 12. System
    def _build_system(self):
        p = self.new_page("System")
        body = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        body.pack(fill="both", expand=True, padx=18, pady=18)
        body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1); body.grid_rowconfigure(0, weight=1)

        left = (ctk.CTkFrame(body, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(body, bg="#151922"))
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        (ctk.CTkLabel if HAS_CTK else tk.Label)(left, text="Hardware & OS Profile", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        self.system_text = tk.Text(left, bg="#151922", fg="#eef2f7", insertbackground="#eef2f7", bd=0, wrap="word", font=("Segoe UI", 10))
        self.system_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        right = (ctk.CTkFrame(body, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(body, bg="#151922"))
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        (ctk.CTkLabel if HAS_CTK else tk.Label)(right, text="Storage Drive Distribution", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 8))
        self.system_drive_table = FilterableTable(right, ["DeviceID", "UsedGB", "FreeGB", "TotalGB", "FileSystem", "VolumeName"], [90, 110, 110, 110, 120, 250], default_sort="FreeGB")
        self.system_drive_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # 13. Reports
    def _build_reports(self):
        p = self.new_page("Reports")
        box = (ctk.CTkFrame(p, corner_radius=12, fg_color="#151922") if HAS_CTK else tk.Frame(p, bg="#151922"))
        box.pack(fill="x", padx=18, pady=18)
        (ctk.CTkLabel if HAS_CTK else tk.Label)(box, text="Audit Reports & Data Export", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=16, pady=(16, 4))
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        btn_cls(box, text="EXPORT FULL JSON SYSTEM AUDIT", command=self.export_audit).pack(anchor="w", padx=16, pady=5)
        btn_cls(box, text="OPEN REPORT & BACKUP FOLDER", command=lambda: os.startfile(APP_DIR)).pack(anchor="w", padx=16, pady=(5, 16))

    def export_audit(self):
        def work():
            data = {
                "generated": datetime.now().isoformat(), "administrator": is_admin(),
                "memory": get_memory(), "system": get_system_info(), "processes": get_processes(),
                "tasks": get_tasks(), "services": get_services(), "startup": get_startup(),
                "applications": get_installed_apps(), "network_adapters": get_network_adapters(),
                "tcp_connections": get_tcp_connections(), "drives": get_drives(), "config": CONFIG
            }
            out = REPORT_DIR / f"OptimusPrime_Audit_{datetime.now():%Y%m%d_%H%M%S}.json"
            out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            log(f"Audit exported: {out}")
            self.after(0, lambda: messagebox.showinfo("Audit Saved", f"Saved:\n{out}"))
        threading.Thread(target=work, daemon=True).start()

    # 14. Log
    def _build_log(self):
        p = self.new_page("Log")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = (ctk.CTkFrame(p, fg_color="transparent") if HAS_CTK else tk.Frame(p, bg="#0b0f14"))
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        btn_cls = ctk.CTkButton if HAS_CTK else tk.Button
        btn_cls(top, text="Refresh Log", command=self.refresh_log).pack(side="left")
        btn_cls(top, text="Clear Log", command=self.clear_log).pack(side="left", padx=6)
        btn_cls(top, text="Open App Folder", command=lambda: os.startfile(APP_DIR)).pack(side="right")

        self.log_box = tk.Text(p, bg="#151922", fg="#eef2f7", insertbackground="#eef2f7", bd=0, wrap="none", font=("Consolas", 9))
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def refresh_log(self):
        try: text = LOG_FILE.read_text(encoding="utf-8") if LOG_FILE.exists() else "No logs recorded."
        except Exception as exc: text = str(exc)
        self.log_box.delete("1.0", "end"); self.log_box.insert("end", text); self.log_box.see("end")

    def clear_log(self):
        if messagebox.askyesno("Clear", "Clear activity log?"):
            try: LOG_FILE.unlink(missing_ok=True)
            except Exception: pass
            self.refresh_log()

    # Data Refresh
    def refresh_all(self):
        if self._is_refreshing: return
        self._is_refreshing = True
        self.set_status("Refreshing…")

        def worker():
            mem = get_memory(); procs = get_processes(); tsks = get_tasks()
            svcs = get_services(); sups = get_startup(); sys_info = get_system_info(); drvs = get_drives()
            self.after(0, lambda: self._apply_refresh(mem, procs, tsks, svcs, sups, sys_info, drvs))
        threading.Thread(target=worker, daemon=True).start()

    def _apply_refresh(self, mem, procs, tsks, svcs, sups, sys_info, drvs):
        try:
            self.memory = mem or {}
            self.processes = list(procs or [])
            self.tasks = list(tsks or [])
            self.services = list(svcs or [])
            self.startups = list(sups or [])
            self.system = sys_info or {}
            self.drives = list(drvs or [])

            self.update_dashboard()
            self.process_table.set_data(self.processes)
            self.task_table.set_data(self.tasks)
            self.service_table.set_data(self.services)
            self.startup_table.set_data(self.startups)
            self.system_drive_table.set_data(self.drives)
            self.storage_table.set_data(self.drives)
            self.refresh_sleep_table()
            self.refresh_log()
            self.apply_system_text()

            admin = is_admin()
            self.sidebar_stats.configure(text=f"RAM {self.memory.get('UsedPct', '—')}%  •  {len(self.processes):,} procs\n{len(self.services):,} svcs  •  {len(self.tasks):,} tasks")
            self.admin_label.configure(text="ADMINISTRATOR" if admin else "STANDARD USER")
            self.badge.configure(text="ADMIN" if admin else "STANDARD")
            self.set_status(f"Updated {datetime.now():%H:%M:%S}")
        finally:
            self._is_refreshing = False
        interval = max(3, int(CONFIG.get("refresh_seconds", 5))) * 1000
        self.after(interval, self.refresh_all)

    def update_dashboard(self):
        self.card_vars["RAM"].set(f"{fmt_gb(self.memory.get('UsedGB'))} / {fmt_gb(self.memory.get('TotalGB'))} GB\n{self.memory.get('UsedPct', '—')}%")
        self.card_vars["PROC"].set(f"{len(self.processes):,}")
        if self.processes:
            top = max(self.processes, key=lambda r: float(r.get("RAM_MB") or 0))
            self.card_vars["TOP"].set(f"{top.get('Name')}\n{fmt_mb(top.get('RAM_MB'))} MB")
            self.dashboard_table.set_data([{"Name": r.get("Name"), "PID": r.get("PID"), "RAM_MB": r.get("RAM_MB"), "CPU_s": r.get("CPU_s"), "Owner": r.get("Owner")} for r in self.processes])
        else:
            self.card_vars["TOP"].set("—"); self.dashboard_table.set_data([])
        c_drive = next((d for d in self.drives if norm(d.get("DeviceID")).upper() == "C:"), None)
        self.card_vars["DISK"].set(f"{fmt_gb(c_drive.get('FreeGB'))} GB free" if c_drive else "—")
        own_task = next((t for t in self.tasks if t.get("TaskName") == TASK_NAME), None)
        self.card_vars["TASK"].set(norm(own_task.get("State")) if own_task else "Not Registered")

    def apply_system_text(self):
        self.system_text.delete("1.0", "end")
        for k, v in self.system.items():
            self.system_text.insert("end", f"{k}: {v}\n")

    def refresh_processes(self): threading.Thread(target=lambda: self._apply_p(get_processes()), daemon=True).start()
    def _apply_p(self, r): self.processes = list(r or []); self.process_table.set_data(self.processes); self.refresh_sleep_table()
    def refresh_tasks(self): threading.Thread(target=lambda: self._apply_t(get_tasks()), daemon=True).start()
    def _apply_t(self, r): self.tasks = list(r or []); self.task_table.set_data(self.tasks)
    def refresh_services(self): threading.Thread(target=lambda: self._apply_s(get_services()), daemon=True).start()
    def _apply_s(self, r): self.services = list(r or []); self.service_table.set_data(self.services)
    def refresh_startup(self): threading.Thread(target=lambda: self._apply_st(get_startup()), daemon=True).start()
    def _apply_st(self, r): self.startups = list(r or []); self.startup_table.set_data(self.startups)
    def refresh_apps(self): threading.Thread(target=lambda: self._apply_a(get_installed_apps()), daemon=True).start()
    def _apply_a(self, r): self.apps = list(r or []); self.app_table.set_data(self.apps)
    def refresh_network(self): threading.Thread(target=lambda: self._apply_n(get_network_adapters(), get_tcp_connections()), daemon=True).start()
    def _apply_n(self, a, t): self.adapters = list(a or []); self.connections = list(t or []); self.adapter_table.set_data(self.adapters); self.tcp_table.set_data(self.connections)
    def refresh_drives(self): threading.Thread(target=lambda: self._apply_d(get_drives()), daemon=True).start()
    def _apply_d(self, r): self.drives = list(r or []); self.storage_table.set_data(self.drives); self.system_drive_table.set_data(self.drives)
    def restart_elevated(self):
        if elevate_current_script(): self.destroy()

# ── 10. ENTRY POINT ───────────────────────────────────────────────────────────
def main():
    if "--scheduled-optimize" in sys.argv:
        scheduled_optimization()
        return
    app = OptimusPrimeStandaloneApp()
    app.mainloop()


if __name__ == "__main__":
    main()
