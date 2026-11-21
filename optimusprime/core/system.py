# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME System, Memory, Storage and Performance Diagnostics
"""
from optimusprime.utils.helpers import ps_json


def get_memory() -> dict:
    """Collect physical memory metrics (Total, Free, Used in GB and %)."""
    data = ps_json(r'''
$os = Get-CimInstance Win32_OperatingSystem
[pscustomobject]@{
    TotalGB = [math]::Round($os.TotalVisibleMemorySize/1MB, 2)
    FreeGB  = [math]::Round($os.FreePhysicalMemory/1MB, 2)
    UsedGB  = [math]::Round(($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/1MB, 2)
    UsedPct = [math]::Round((($os.TotalVisibleMemorySize - $os.FreePhysicalMemory)/$os.TotalVisibleMemorySize)*100, 1)
} | ConvertTo-Json -Compress
''', timeout=20)
    return data or {}


def get_system_info() -> dict:
    """Retrieve hardware and operating system profile."""
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
''', timeout=30)
    return data or {}


def get_drives() -> list:
    """Enumerate fixed logical drives with storage stats."""
    data = ps_json(r'''
Get-CimInstance Win32_LogicalDisk -Filter "DriveType=3" |
Select-Object DeviceID,
    @{N="UsedGB"; E={[math]::Round(($_.Size - $_.FreeSpace)/1GB, 2)}},
    @{N="FreeGB"; E={[math]::Round($_.FreeSpace/1GB, 2)}},
    @{N="TotalGB"; E={[math]::Round($_.Size/1GB, 2)}},
    FileSystem, VolumeName |
ConvertTo-Json -Depth 3
''', timeout=30)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def get_performance_sample() -> dict:
    """Capture a lightweight instant snapshot of CPU, RAM, and Network transfer."""
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
''', timeout=20)
    return data or {}
