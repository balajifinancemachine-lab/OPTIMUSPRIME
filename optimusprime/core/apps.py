# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Installed Applications Inventory (Win32 & AppX Packages)
"""
from optimusprime.utils.helpers import ps_json


def get_installed_apps() -> list:
    """Enumerate installed Win32 software and modern AppX packages."""
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
    data = ps_json(script, timeout=120)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data
