# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME - Ultimate Windows System Optimizer & Administrator
"""
import sys
from optimusprime.utils.constants import APP_NAME, APP_SUBTITLE, APP_VERSION
from optimusprime.utils.elevation import is_admin, elevate_current_script, enable_debug_privilege
from optimusprime.utils.self_healing import heal_all_dependencies, suppress_console
from optimusprime.core.maintenance import scheduled_optimization
from optimusprime.ui.app import OptimusPrimeApp

__version__ = APP_VERSION
__author__ = "OPTIMUSPRIME Team"
__all__ = ["OptimusPrimeApp", "main", "APP_NAME", "APP_SUBTITLE", "APP_VERSION"]


def main():
    """Main application execution lifecycle with self-healing and auto-elevation."""
    # Step 1: Suppress console window if launched with python.exe
    suppress_console()

    # Step 2: Enable Windows token debug privileges
    enable_debug_privilege()

    # Step 3: Check for headless scheduled optimizer mode
    if "--scheduled-optimize" in sys.argv:
        scheduled_optimization()
        return

    # Step 4: Self-healing auto-elevation (Administrator UAC)
    if not is_admin() and "--elevated" not in sys.argv:
        if elevate_current_script():
            sys.exit(0)

    # Step 5: Self-healing dependency verification
    heal_all_dependencies()

    # Step 6: Launch CustomTkinter GUI
    app = OptimusPrimeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
