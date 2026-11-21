# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Process Management, Memory Trimming, Suspension, and Safe Termination
"""
import ctypes
from optimusprime.utils.helpers import ps_json, run_cmd
from optimusprime.utils.logger import log

PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_SET_QUOTA = 0x0100


def get_processes() -> list:
    """Collect process inventory with PID, Name, RAM, CPU time, Owner, and Path."""
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
''', timeout=70)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def minimize_pid_set() -> set:
    """Return set of PIDs that currently possess minimized (iconic) windows."""
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
    data = ps_json(script, timeout=30)
    if data is None:
        return set()
    if isinstance(data, list):
        return {int(v) for v in data if str(v).isdigit()}
    try:
        return {int(data)}
    except Exception:
        return set()


def suspend_process(pid: int):
    """Suspend a process via native NT API NtSuspendProcess."""
    try:
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
        if not handle:
            return False, "OpenProcess failed"
        status = ctypes.windll.ntdll.NtSuspendProcess(handle)
        ctypes.windll.kernel32.CloseHandle(handle)
        return status == 0, f"NTSTATUS={status}"
    except Exception as exc:
        return False, str(exc)


def resume_process(pid: int):
    """Resume a suspended process via native NT API NtResumeProcess."""
    try:
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SUSPEND_RESUME, False, int(pid))
        if not handle:
            return False, "OpenProcess failed"
        status = ctypes.windll.ntdll.NtResumeProcess(handle)
        ctypes.windll.kernel32.CloseHandle(handle)
        return status == 0, f"NTSTATUS={status}"
    except Exception as exc:
        return False, str(exc)


def trim_working_set(pid: int):
    """Flush and minimize the process working set back to paging store."""
    try:
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_SET_QUOTA, False, int(pid))
        if not handle:
            return False, "OpenProcess failed"
        fn = ctypes.windll.kernel32.SetProcessWorkingSetSize
        fn.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
        fn.restype = ctypes.c_bool
        ok = fn(handle, ctypes.c_size_t(-1).value, ctypes.c_size_t(-1).value)
        ctypes.windll.kernel32.CloseHandle(handle)
        return bool(ok), ""
    except Exception as exc:
        return False, str(exc)


def terminate_pids(pids: list):
    """Safely terminate a list of PIDs with diagnostic logging."""
    good = 0
    errors = []
    for pid in pids:
        result = run_cmd(["taskkill.exe", "/PID", str(pid), "/F"], timeout=12)
        if result.returncode == 0:
            good += 1
        else:
            errors.append(f"PID {pid}: {(result.stderr or result.stdout).strip()}")
    return good, errors
