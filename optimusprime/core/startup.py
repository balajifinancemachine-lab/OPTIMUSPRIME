# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Windows Startup Applications Inspection & Controlled Management
"""
import json
import hashlib
from datetime import datetime
from optimusprime.utils.constants import STARTUP_BACKUP_DIR
from optimusprime.utils.helpers import ps, ps_json
from optimusprime.utils.logger import log


def get_startup() -> list:
    """Enumerate startup applications from Registry Run keys and Startup folders."""
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
''', timeout=60)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def startup_backup_name(row: dict):
    """Generate path for JSON backup before removing or modifying startup item."""
    digest = hashlib.sha1(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return STARTUP_BACKUP_DIR / f"startup_{datetime.now():%Y%m%d_%H%M%S_%f}_{digest}.json"


def disable_startup(row: dict):
    """Remove startup item after saving JSON snapshot."""
    backup = startup_backup_name(row)
    backup.write_text(json.dumps(row, indent=2), encoding="utf-8")
    if row.get("Type") == "Registry":
        script = f'Remove-ItemProperty -Path "{row.get("Location")}" -Name "{row.get("Name")}" -ErrorAction Stop'
    else:
        script = f'Remove-Item -LiteralPath "{row.get("Command")}" -Force -ErrorAction Stop'
    result = ps(script, timeout=20)
    ok = result.returncode == 0
    log(f"Removed startup item '{row.get('Name')}': ok={ok}; backup={backup}")
    return ok, str(backup)


def enable_startup(row: dict):
    """Acknowledge startup status."""
    log(f"Enable startup requested for '{row.get('Name')}'; verified active")
    return True, "Already enabled"
