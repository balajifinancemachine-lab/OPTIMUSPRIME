# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Network Adapter & Active TCP Connections Diagnostics
"""
from optimusprime.utils.helpers import ps_json


def get_network_adapters() -> list:
    """Retrieve network adapters, link speeds, media types, and connection state."""
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
''', timeout=45)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data


def get_tcp_connections() -> list:
    """List active established TCP connections mapped to originating processes."""
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
''', timeout=60)
    if not data:
        return []
    return [data] if isinstance(data, dict) else data
