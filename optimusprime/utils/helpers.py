# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME System Helpers and Native Windows API Bridges
"""
import os
import json
import hashlib
import subprocess
from pathlib import Path
from optimusprime.utils.constants import CREATE_NO_WINDOW, ICON_DIR
from optimusprime.utils.logger import log


def norm(value) -> str:
    """Normalize string, stripping whitespace and nulls."""
    return str(value if value is not None else "").strip()


def name_key(value) -> str:
    """Generate normalized lookup key for process or application names."""
    return norm(value).lower().replace(".exe", "")


def fmt_mb(value) -> str:
    """Format numeric value in Megabytes."""
    try:
        return f"{float(value):,.1f}"
    except Exception:
        return "0.0"


def fmt_gb(value) -> str:
    """Format numeric value in Gigabytes."""
    try:
        return f"{float(value):,.2f}"
    except Exception:
        return "0.00"


def run_cmd(args, timeout=30):
    """Run an external command without flashing a console window."""
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
    except Exception as exc:
        class Failed:
            returncode = -1
            stdout = ""
            stderr = str(exc)
        return Failed()


def ps(script: str, timeout: int = 30):
    """Run a PowerShell command silently with Bypass execution policy."""
    return run_cmd(
        ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        timeout,
    )


def ps_json(script: str, timeout: int = 30):
    """Execute PowerShell and parse JSON output safely."""
    result = ps(script, timeout)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout.strip())
    except Exception as exc:
        log(f"PowerShell JSON parse error: {exc}; output={result.stdout[:300]}")
        return None


def icon_cache_path(exe_path: str, size: int = 32) -> Path:
    """Return cached file path for an extracted executable icon."""
    digest = hashlib.sha1(f"{exe_path}|{size}".encode("utf-8", errors="ignore")).hexdigest()
    return ICON_DIR / f"{digest}.png"


def extract_windows_icon(exe_path: str, size: int = 32):
    """Extract Windows icon from executable or shortcut with caching."""
    if not exe_path or not Path(exe_path).exists():
        return None
    target = icon_cache_path(exe_path, size)
    if target.exists():
        return target
    escaped = str(exe_path).replace("'", "''")
    escaped_target = str(target).replace("'", "''")
    script = f'''
Add-Type -AssemblyName System.Drawing
try {{
    $icon = [System.Drawing.Icon]::ExtractAssociatedIcon('{escaped}')
    if ($icon) {{
        $bmp = New-Object System.Drawing.Bitmap {size}, {size}
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.Clear([System.Drawing.Color]::Transparent)
        $g.DrawIcon($icon, 0, 0)
        $bmp.Save('{escaped_target}', [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose(); $bmp.Dispose(); $icon.Dispose()
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
