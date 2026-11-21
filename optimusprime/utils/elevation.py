# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Elevation, UAC Management, and Privilege Escalation
"""
import sys
import ctypes
import subprocess
from pathlib import Path
from optimusprime.utils.logger import log


def is_admin() -> bool:
    """Check if the current process has Windows Administrator rights."""
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def enable_debug_privilege() -> bool:
    """Enable SeDebugPrivilege in current token for full process inspection & control."""
    try:
        import win32api
        import win32security
        flags = win32security.TOKEN_ADJUST_PRIVILEGES | win32security.TOKEN_QUERY
        h_token = win32security.OpenProcessToken(win32api.GetCurrentProcess(), flags)
        priv_id = win32security.LookupPrivilegeValue(None, "SeDebugPrivilege")
        win32security.AdjustTokenPrivileges(
            h_token, 0, [(priv_id, win32security.SE_PRIVILEGE_ENABLED)]
        )
        return True
    except Exception:
        # Fallback via direct ctypes NT API
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
            tp.Privileges[0].Attributes = 0x00000002  # SE_PRIVILEGE_ENABLED

            ok = advapi32.AdjustTokenPrivileges(h_token, False, ctypes.byref(tp), 0, None, None)
            kernel32.CloseHandle(h_token)
            return bool(ok)
        except Exception as exc:
            log(f"Debug privilege escalation notice: {exc}")
            return False


def elevate_current_script() -> bool:
    """Relaunches the script elevated using ShellExecuteW 'runas'."""
    try:
        script = str(Path(sys.argv[0]).resolve())
        args = [script] + [a for a in sys.argv[1:] if a != "--elevated"]
        command_line = subprocess.list2cmdline(args)
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, command_line, None, 1
        )
        return rc > 32
    except Exception as exc:
        log(f"Elevation failed: {exc}")
        return False
