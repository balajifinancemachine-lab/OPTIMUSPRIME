# -*- coding: utf-8 -*-
"""
PC Optimizer Compatibility Launcher
Redirects to the standalone self-healing optimizer file.
"""
import runpy
from pathlib import Path

target = Path(__file__).parent / "optimusprime.pyw"
if target.exists():
    runpy.run_path(str(target), run_name="__main__")
else:
    from optimusprime import main
    main()
