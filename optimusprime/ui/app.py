# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Main Application Interface & Navigation Engine
"""
import os
import sys
import json
import time
import threading
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image

from optimusprime.utils.constants import (
    APP_NAME, APP_SUBTITLE, TASK_NAME, APP_DIR, REPORT_DIR,
    PROTECTED_PROCESSES, PROTECTED_SERVICE_NAMES
)
from optimusprime.utils.logger import log
from optimusprime.utils.config import CONFIG, save_config
from optimusprime.utils.elevation import is_admin, elevate_current_script
from optimusprime.utils.helpers import (
    norm, name_key, fmt_mb, fmt_gb, run_cmd, extract_windows_icon
)
from optimusprime.ui.theme import THEME, FONT_FAMILY, FONT_TITLE, FONT_HEADING, FONT_BODY
from optimusprime.ui.table import FilterableTable
from optimusprime.core import (
    get_memory, get_system_info, get_drives, get_performance_sample,
    get_processes, minimize_pid_set, suspend_process, resume_process,
    trim_working_set, terminate_pids,
    get_services, service_action,
    get_tasks, full_task_name, delete_task, task_enable, task_run, create_optimizer_task,
    get_startup, disable_startup, enable_startup,
    get_network_adapters, get_tcp_connections,
    get_installed_apps,
    cleanup_temp, flush_dns, refresh_explorer, empty_recycle_bin,
    component_cleanup, scheduled_optimization
)


class OptimusPrimeApp(ctk.CTk):
    """OPTIMUSPRIME Windows Administration, Performance & Optimization GUI."""

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(f"{APP_NAME} — {APP_SUBTITLE}")
        self.geometry("1580x960")
        self.minsize(1180, 720)
        self.configure(fg_color=THEME["bg_main"])

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
        self._build_all_pages()

        saved_page = CONFIG.get("last_page", "Dashboard")
        if saved_page not in self.pages:
            saved_page = "Dashboard"
        self.select_page(saved_page)

        # Background schedules
        self.after(300, self.refresh_all)
        self.after(1000, self.auto_sleep_tick)
        self.after(1500, self.update_performance_loop)

    # ── Application Shell & Navigation ───────────────────────────────────────
    def _build_shell(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=THEME["bg_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        ctk.CTkLabel(self.sidebar, text="⚡ OPTIMUSPRIME", font=FONT_TITLE, text_color=THEME["text_main"]).pack(
            anchor="w", padx=18, pady=(20, 0)
        )
        ctk.CTkLabel(self.sidebar, text="ULTIMATE SYSTEM CONTROL", font=(FONT_FAMILY, 8, "bold"),
                     text_color=THEME["text_muted"]).pack(anchor="w", padx=18, pady=(0, 16))

        page_names = [
            "Dashboard", "Processes", "App Sleep", "Scheduled Tasks", "Services",
            "Startup", "Applications", "Network", "Performance", "Storage",
            "Maintenance", "System", "Reports", "Log"
        ]
        self.nav_buttons = {}
        for name in page_names:
            btn = ctk.CTkButton(
                self.sidebar, text=name, anchor="w", height=36, corner_radius=8,
                fg_color="transparent", hover_color=THEME["bg_card_hover"],
                font=(FONT_FAMILY, 11),
                command=lambda n=name: self.select_page(n)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[name] = btn

        # Sidebar Footer
        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=12, pady=14)

        admin = is_admin()
        self.admin_label = ctk.CTkLabel(
            footer, text="ADMINISTRATOR" if admin else "STANDARD USER",
            text_color=THEME["success"] if admin else THEME["warning"],
            font=(FONT_FAMILY, 10, "bold")
        )
        self.admin_label.pack(anchor="w")

        self.sidebar_stats = ctk.CTkLabel(
            footer, text="Initializing…", text_color=THEME["text_muted"],
            justify="left", font=(FONT_FAMILY, 9)
        )
        self.sidebar_stats.pack(anchor="w", pady=(4, 0))

        if not admin:
            ctk.CTkButton(
                footer, text="Restart Elevated", height=32,
                fg_color=THEME["primary"], hover_color=THEME["primary_hover"],
                command=self.restart_elevated
            ).pack(fill="x", pady=(8, 0))

        # Main Viewport
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=THEME["bg_main"])
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(1, weight=1)
        main.grid_columnconfigure(0, weight=1)
        self.main = main

        # Top Bar
        top = ctk.CTkFrame(main, height=64, corner_radius=0, fg_color=THEME["bg_main"])
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)

        self.page_title = ctk.CTkLabel(top, text=APP_NAME, font=FONT_TITLE)
        self.page_title.grid(row=0, column=0, padx=20, pady=(10, 0), sticky="w")
        self.global_status = ctk.CTkLabel(top, text="Ready", text_color=THEME["text_muted"], font=(FONT_FAMILY, 10))
        self.global_status.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        self.badge = ctk.CTkLabel(
            top, text="ADMIN" if admin else "STANDARD",
            text_color=THEME["success"] if admin else THEME["warning"],
            font=(FONT_FAMILY, 10, "bold")
        )
        self.badge.grid(row=0, column=2, padx=12)

        ctk.CTkButton(
            top, text="⟳ Refresh", width=90, height=32,
            fg_color=THEME["bg_card"], hover_color=THEME["bg_card_hover"],
            command=self.refresh_all
        ).grid(row=0, column=3, rowspan=2, padx=12)

        # Content Container
        self.content = ctk.CTkFrame(main, fg_color="transparent", corner_radius=0)
        self.content.grid(row=1, column=0, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.pages = {}

    def select_page(self, name):
        """Navigate to specific application page."""
        if name in self.pages:
            self.page_title.configure(text=name)
            self.pages[name].tkraise()
            for n, b in self.nav_buttons.items():
                b.configure(fg_color=THEME["primary"] if n == name else "transparent")
            CONFIG["last_page"] = name
            save_config()

    def set_status(self, text):
        """Update top bar global status message."""
        self.global_status.configure(text=str(text))

    def new_page(self, name):
        """Instantiate new page frame."""
        p = ctk.CTkFrame(self.content, fg_color="transparent")
        p.grid(row=0, column=0, sticky="nsew")
        p.grid_rowconfigure(0, weight=1)
        p.grid_columnconfigure(0, weight=1)
        self.pages[name] = p
        return p

    def _build_all_pages(self):
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

    # ── 1. Dashboard ─────────────────────────────────────────────────────────
    def _card(self, parent, key, title, col):
        frame = ctk.CTkFrame(parent, corner_radius=12, fg_color=THEME["bg_card"])
        frame.grid(row=0, column=col, sticky="ew", padx=6, pady=4)
        ctk.CTkLabel(frame, text=title, text_color=THEME["text_muted"], font=(FONT_FAMILY, 9, "bold")).pack(
            anchor="w", padx=14, pady=(10, 0)
        )
        var = tk.StringVar(value="—")
        ctk.CTkLabel(frame, textvariable=var, font=(FONT_FAMILY, 16, "bold")).pack(
            anchor="w", padx=14, pady=(4, 12)
        )
        self.card_vars[key] = var

    def _build_dashboard(self):
        p = self.new_page("Dashboard")
        p.grid_rowconfigure(2, weight=1)
        p.grid_columnconfigure(0, weight=1)

        # Row 0: Header Banner
        head = ctk.CTkFrame(p, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=18, pady=(8, 6))
        ctk.CTkLabel(head, text="System Health & Live Monitoring", font=FONT_HEADING).pack(side="left")
        ctk.CTkLabel(head, text="Real-time status, process control, and self-healing automation",
                     text_color=THEME["text_muted"]).pack(side="left", padx=12)
        ctk.CTkButton(
            head, text="⚡ Smart Optimize", width=140, height=34,
            fg_color=THEME["primary"], hover_color=THEME["primary_hover"],
            command=self.smart_optimize
        ).pack(side="right")

        # Row 1: KPI Summary Cards (Cleanly separated!)
        self.card_vars = {}
        cards = ctk.CTkFrame(p, fg_color="transparent")
        cards.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 10))
        for i in range(5):
            cards.grid_columnconfigure(i, weight=1)
        for i, (k, t) in enumerate([
            ("RAM", "Physical Memory"), ("PROC", "Active Processes"),
            ("TOP", "Top Memory User"), ("DISK", "Drive C: Free"),
            ("TASK", "Optimizer Task")
        ]):
            self._card(cards, k, t, i)

        # Row 2: Main Split Panel
        body = ctk.CTkFrame(p, fg_color="transparent")
        body.grid(row=2, column=0, sticky="nsew", padx=18, pady=(0, 18))
        body.grid_columnconfigure(0, weight=3)
        body.grid_columnconfigure(1, weight=2)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, corner_radius=12, fg_color=THEME["bg_card"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(left, text="Top Memory Consumers", font=FONT_HEADING).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        self.dashboard_table = FilterableTable(
            left, ["Name", "PID", "RAM_MB", "CPU_s", "Owner"],
            [220, 70, 95, 85, 240], default_sort="RAM_MB"
        )
        self.dashboard_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        right = ctk.CTkFrame(body, corner_radius=12, fg_color=THEME["bg_card"])
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ctk.CTkLabel(right, text="Quick Management Center", font=FONT_HEADING).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        for text, cmd in [
            ("◌ App Sleep Management", lambda: self.select_page("App Sleep")),
            ("☷ Scheduled Tasks Control", lambda: self.select_page("Scheduled Tasks")),
            ("⚙ Windows Services Manager", lambda: self.select_page("Services")),
            ("↥ Startup Applications", lambda: self.select_page("Startup")),
            ("▣ Installed Applications", lambda: self.select_page("Applications")),
            ("▤ Export Full JSON Audit", self.export_audit),
        ]:
            ctk.CTkButton(
                right, text=text, height=38, fg_color="#1e2430",
                hover_color=THEME["bg_card_hover"], anchor="w",
                font=(FONT_FAMILY, 11), command=cmd
            ).pack(fill="x", padx=14, pady=4)

        self.dashboard_note = ctk.CTkLabel(
            right, text="", text_color=THEME["text_muted"],
            justify="left", wraplength=360, font=(FONT_FAMILY, 9)
        )
        self.dashboard_note.pack(anchor="w", padx=14, pady=14)

    # ── 2. Processes ─────────────────────────────────────────────────────────
    def _build_processes(self):
        p = self.new_page("Processes")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        for text, cmd in [
            ("Sleep", self.sleep_selected),
            ("Wake", self.wake_selected),
            ("Trim Working Set", self.trim_selected),
            ("Terminate", self.terminate_selected)
        ]:
            ctk.CTkButton(bar, text=text, command=cmd).pack(side="left", padx=3)

        ctk.CTkButton(
            bar, text="END ALL FILTERED USER PROCESSES",
            fg_color=THEME["danger"], hover_color=THEME["danger_hover"],
            command=self.end_filtered_user
        ).pack(side="right")

        self.process_table = FilterableTable(
            p, ["PID", "Name", "RAM_MB", "CPU_s", "Owner", "SessionId", "Path", "CommandLine"],
            [70, 180, 95, 85, 200, 80, 500, 600], default_sort="RAM_MB"
        )
        self.process_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def sleep_selected(self):
        rows = self.process_table.selected_rows()
        if not rows:
            return messagebox.showinfo("Sleep", "Please select one or more processes.")
        for r in rows:
            pname = name_key(r.get("Name"))
            pid = int(r.get("PID", 0) or 0)
            if pname in PROTECTED_PROCESSES:
                continue
            ok, detail = suspend_process(pid)
            log(f"Suspended {pname} PID={pid}: ok={ok} {detail}")
        self.refresh_processes()

    def wake_selected(self):
        rows = self.process_table.selected_rows()
        if not rows:
            return messagebox.showinfo("Wake", "Please select one or more processes.")
        for r in rows:
            pid = int(r.get("PID", 0) or 0)
            ok, detail = resume_process(pid)
            log(f"Resumed {r.get('Name')} PID={pid}: ok={ok} {detail}")
        self.refresh_processes()

    def trim_selected(self):
        rows = self.process_table.selected_rows()
        if not rows:
            return messagebox.showinfo("Trim", "Please select one or more processes.")
        done = 0
        for r in rows:
            if name_key(r.get("Name")) in PROTECTED_PROCESSES:
                continue
            ok, detail = trim_working_set(int(r.get("PID", 0) or 0))
            done += int(ok)
        self.set_status(f"Trimmed working set for {done}/{len(rows)} processes")
        self.refresh_processes()

    def terminate_selected(self):
        rows = [r for r in self.process_table.selected_rows() if name_key(r.get("Name")) not in PROTECTED_PROCESSES]
        if not rows:
            return messagebox.showwarning("Terminate", "No eligible non-protected process selected.")
        if not messagebox.askyesno("Confirm Termination", f"Force close {len(rows)} selected process(es)?\nUnsaved work will be lost."):
            return
        n, errors = terminate_pids([int(r["PID"]) for r in rows])
        for e in errors:
            log(e)
        self.set_status(f"Terminated {n}/{len(rows)} processes")
        self.refresh_all()

    def end_filtered_user(self):
        if not is_admin():
            return messagebox.showwarning("Administrator", "Please elevate the application to terminate user processes.")
        me = name_key(os.environ.get("USERNAME"))
        rows = []
        for r in self.process_table.filtered:
            owner = norm(r.get("Owner")).lower()
            pname = name_key(r.get("Name"))
            pid = int(r.get("PID", 0) or 0)
            if pid > 4 and pname not in PROTECTED_PROCESSES and (not owner or owner.endswith("\\" + me)):
                rows.append(r)
        if not rows:
            return messagebox.showinfo("Mass Termination", "The current filtered view contains no eligible user processes.")
        preview = "\n".join(f"{r['Name']} (PID {r['PID']})" for r in rows[:30])
        more = f"\n… plus {len(rows) - 30} more" if len(rows) > 30 else ""
        if not messagebox.askyesno("DANGER: END FILTERED PROCESSES", f"Force terminate {len(rows)} filtered user process(es)?\n\n{preview}{more}"):
            return
        n, errors = terminate_pids([int(r["PID"]) for r in rows])
        for e in errors:
            log(e)
        self.set_status(f"Mass terminated {n}/{len(rows)} processes")
        self.refresh_all()

    # ── 3. App Sleep ─────────────────────────────────────────────────────────
    def _build_app_sleep(self):
        p = self.new_page("App Sleep")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        rule = ctk.CTkFrame(p, corner_radius=12, fg_color=THEME["bg_card"])
        rule.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        rule.grid_columnconfigure(1, weight=1)

        self.sleep_enabled_var = tk.BooleanVar(value=bool(CONFIG.get("auto_sleep_enabled")))
        self.sleep_minutes_var = tk.StringVar(value=str(CONFIG.get("auto_sleep_after_minutes", 10)))
        self.sleep_rule_var = tk.StringVar(value=", ".join(CONFIG.get("auto_sleep_processes", ["msedge.exe"])))
        self.scheduled_sleep_var = tk.BooleanVar(value=bool(CONFIG.get("scheduled_auto_sleep")))

        ctk.CTkCheckBox(
            rule, text="Enable automatic sleep for minimized matching apps",
            variable=self.sleep_enabled_var, command=self.save_sleep_settings
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=14, pady=(12, 6))

        ctk.CTkLabel(rule, text="Minutes Minimized").grid(row=1, column=0, sticky="w", padx=14, pady=4)
        ctk.CTkEntry(rule, textvariable=self.sleep_minutes_var, width=80).grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ctk.CTkLabel(rule, text="Target Process Rules").grid(row=2, column=0, sticky="w", padx=14, pady=4)
        ctk.CTkEntry(rule, textvariable=self.sleep_rule_var).grid(row=2, column=1, sticky="ew", padx=8, pady=4)

        ctk.CTkCheckBox(
            rule, text="Integrate these rules into the Scheduled Background Optimizer",
            variable=self.scheduled_sleep_var, command=self.save_sleep_settings
        ).grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(4, 12))

        btns = ctk.CTkFrame(rule, fg_color="transparent")
        btns.grid(row=1, column=2, rowspan=2, padx=14, sticky="e")
        ctk.CTkButton(btns, text="Select Processes", command=self.open_process_picker).pack(side="top", pady=3)
        ctk.CTkButton(btns, text="Find Minimized", command=self.find_sleep_candidates).pack(side="top", pady=3)
        ctk.CTkButton(btns, text="Save Rules", command=self.save_sleep_settings).pack(side="top", pady=3)

        self.sleep_table = FilterableTable(
            p, ["PID", "Name", "RAM_MB", "Minimized", "Path"],
            [80, 200, 100, 100, 800], default_sort="RAM_MB"
        )
        self.sleep_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))

        bottom = ctk.CTkFrame(p, fg_color="transparent")
        bottom.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 14))
        ctk.CTkButton(bottom, text="Sleep Selected", command=self.sleep_sleep_rows).pack(side="left", padx=3)
        ctk.CTkButton(bottom, text="Wake Selected", command=self.wake_sleep_rows).pack(side="left", padx=3)
        ctk.CTkLabel(bottom, text="💡 Suspended processes free up CPU cycles and allow RAM compaction.",
                     text_color=THEME["text_muted"]).pack(side="right")

    def save_sleep_settings(self):
        try:
            m = max(1, int(self.sleep_minutes_var.get()))
        except Exception:
            m = 10
            self.sleep_minutes_var.set("10")
        CONFIG["auto_sleep_enabled"] = bool(self.sleep_enabled_var.get())
        CONFIG["auto_sleep_after_minutes"] = m
        CONFIG["auto_sleep_processes"] = [x.strip() for x in self.sleep_rule_var.get().split(",") if x.strip()]
        CONFIG["scheduled_auto_sleep"] = bool(self.scheduled_sleep_var.get())
        save_config()
        self.set_status("App Sleep settings saved successfully")

    def open_process_picker(self):
        picker = ctk.CTkToplevel(self)
        picker.title("Select Applications & Processes")
        picker.geometry("740x680")
        picker.transient(self)

        top = ctk.CTkFrame(picker, fg_color="transparent")
        top.pack(fill="x", padx=12, pady=10)
        search = tk.StringVar()
        ctk.CTkEntry(top, textvariable=search, placeholder_text="Search process name or path…").pack(
            side="left", fill="x", expand=True
        )

        list_frame = ctk.CTkScrollableFrame(picker)
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        rows = self.processes[:]
        selected = {name_key(x) for x in CONFIG.get("auto_sleep_processes", [])}
        icon_refs = []

        def render():
            for w in list_frame.winfo_children():
                w.destroy()
            q = search.get().lower().strip()
            seen = set()
            for r in rows:
                pname = name_key(r.get("Name"))
                path = norm(r.get("Path"))
                key = (pname, path.lower())
                if key in seen:
                    continue
                seen.add(key)
                text = f"{r.get('Name', '')}   •   {path}"
                if q and q not in text.lower():
                    continue

                f = ctk.CTkFrame(list_frame, fg_color=THEME["bg_card"], corner_radius=8)
                f.pack(fill="x", pady=3)
                var = tk.BooleanVar(value=pname in selected)

                icon_path = extract_windows_icon(path, 32) if path else None
                icon = None
                if icon_path:
                    try:
                        img = Image.open(icon_path).convert("RGBA").resize((26, 26), Image.LANCZOS)
                        icon = ctk.CTkImage(img, size=(26, 26))
                        icon_refs.append(icon)
                    except Exception:
                        icon = None

                if icon:
                    ctk.CTkLabel(f, text="", image=icon, width=32).pack(side="left", padx=6)
                else:
                    ctk.CTkLabel(f, text="⚡", width=32).pack(side="left")

                ctk.CTkCheckBox(f, text=text, variable=var).pack(side="left", fill="x", expand=True, padx=6, pady=6)

                def bind(v=var, n=pname):
                    def fn(*_):
                        if v.get():
                            selected.add(n)
                        else:
                            selected.discard(n)
                    return fn
                var.trace_add("write", bind())

        search.trace_add("write", lambda *_: render())
        render()

        ctk.CTkButton(
            picker, text="Apply Selection",
            command=lambda: (
                self.sleep_rule_var.set(", ".join(sorted(x + ".exe" for x in selected))),
                self.save_sleep_settings(),
                picker.destroy()
            )
        ).pack(pady=(0, 12))

    def find_sleep_candidates(self):
        minimized = minimize_pid_set()
        rows = []
        for r in self.processes:
            pid = int(r.get("PID", 0) or 0)
            pname = name_key(r.get("Name"))
            if pid in minimized and pname not in PROTECTED_PROCESSES:
                rows.append({
                    "PID": pid, "Name": r.get("Name"),
                    "RAM_MB": r.get("RAM_MB"), "Minimized": "Yes",
                    "Path": r.get("Path")
                })
        self.sleep_table.set_data(rows)
        self.set_status(f"Identified {len(rows)} minimized process candidates")

    def refresh_sleep_table(self):
        minimized = minimize_pid_set()
        rules = {name_key(x) for x in CONFIG.get("auto_sleep_processes", [])}
        rows = []
        for r in self.processes:
            pid = int(r.get("PID", 0) or 0)
            pname = name_key(r.get("Name"))
            if pname in rules or pid in minimized:
                rows.append({
                    "PID": pid, "Name": r.get("Name"),
                    "RAM_MB": r.get("RAM_MB"),
                    "Minimized": "Yes" if pid in minimized else "No",
                    "Path": r.get("Path")
                })
        self.sleep_table.set_data(rows)

    def sleep_sleep_rows(self):
        for r in self.sleep_table.selected_rows():
            if name_key(r.get("Name")) in PROTECTED_PROCESSES:
                continue
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
                    if not pid or pname not in rules or pname in PROTECTED_PROCESSES:
                        continue
                    if pid in minimized:
                        started = self.auto_sleep_started.setdefault(pid, now)
                        if now - started >= minutes * 60:
                            ok, detail = suspend_process(pid)
                            log(f"Auto-slept {pname} PID={pid}: ok={ok} {detail}")
                            self.auto_sleep_started[pid] = now + 86400 if ok else now
                    else:
                        self.auto_sleep_started.pop(pid, None)
        except Exception as exc:
            log(f"Auto-sleep routine exception: {exc}")
        self.after(30000, self.auto_sleep_tick)

    # ── 4. Scheduled Tasks ───────────────────────────────────────────────────
    def _build_tasks(self):
        p = self.new_page("Scheduled Tasks")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)

        self.task_interval = tk.StringVar(value="60")
        ctk.CTkLabel(bar, text="Optimizer Interval").pack(side="left")
        ctk.CTkComboBox(
            bar, variable=self.task_interval, values=["15", "30", "60", "120", "360", "720", "1440"],
            width=85, state="readonly"
        ).pack(side="left", padx=6)

        ctk.CTkButton(bar, text="Create / Update Optimizer", command=self.create_optimizer_task_ui).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="Enable Filtered", command=lambda: self.bulk_tasks("enable")).pack(side="left", padx=3)
        ctk.CTkButton(bar, text="Disable Filtered", command=lambda: self.bulk_tasks("disable")).pack(side="left", padx=3)
        ctk.CTkButton(bar, text="Run Filtered", command=lambda: self.bulk_tasks("run")).pack(side="left", padx=3)
        ctk.CTkButton(
            bar, text="Delete Filtered + XML",
            fg_color=THEME["danger"], hover_color=THEME["danger_hover"],
            command=lambda: self.bulk_tasks("delete")
        ).pack(side="left", padx=3)

        self.task_table = FilterableTable(
            p, ["TaskName", "TaskPath", "State", "Author", "RunLevel", "LastRun", "NextRun", "Category", "Scope", "OptimizerOwned", "Actions"],
            [220, 240, 90, 160, 100, 160, 160, 140, 140, 110, 480],
            default_sort="TaskName", category_field="Category"
        )
        self.task_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def create_optimizer_task_ui(self):
        if not is_admin():
            return messagebox.showwarning("Administrator", "Please elevate the application to create scheduled tasks.")
        try:
            m = max(15, int(self.task_interval.get()))
        except Exception:
            return messagebox.showerror("Interval", "Invalid interval value.")
        CONFIG["scheduled_clean_temp"] = True
        CONFIG["scheduled_flush_dns"] = True
        save_config()
        try:
            create_optimizer_task(m)
            self.refresh_tasks()
            messagebox.showinfo("Scheduled Automation", f"Registered task '{TASK_NAME}'\nRunning every {m} minutes.")
        except Exception as exc:
            messagebox.showerror("Task Scheduler", str(exc))

    def bulk_tasks(self, action):
        rows = self.task_table.filtered
        if not rows:
            return messagebox.showinfo("Tasks", "No tasks in the current filtered view.")
        protected = [r for r in rows if r.get("Category") == "Microsoft" or norm(r.get("TaskPath")).lower().startswith("\\microsoft\\")]
        target = [r for r in rows if r not in protected] if protected else rows
        if action == "delete" and not target:
            return messagebox.showwarning("Bulk Delete", "The filtered view contains only Microsoft/System tasks. Please filter to custom tasks.")
        if not target:
            return messagebox.showinfo("Tasks", "No eligible non-Microsoft tasks in the current filter.")
        title = {"enable": "Enable", "disable": "Disable", "run": "Run", "delete": "Delete"}[action]
        if not messagebox.askyesno(f"Bulk {title}", f"{title} {len(target)} eligible task(s)?\n(System/Microsoft tasks are automatically skipped)"):
            return
        done = 0
        for r in target:
            full = full_task_name(r.get("TaskPath"), r.get("TaskName"))
            if action == "delete":
                ok, _ = delete_task(full)
            elif action == "run":
                ok = task_run(full)
            else:
                ok = task_enable(full, action == "enable")
            done += int(ok)
        self.set_status(f"Tasks {title}: {done}/{len(target)}")
        self.refresh_tasks()

    # ── 5. Services ──────────────────────────────────────────────────────────
    def _build_services(self):
        p = self.new_page("Services")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        ctk.CTkLabel(bar, text="Batch actions apply to current filter. Core Windows & Security services are protected.",
                     text_color=THEME["text_muted"]).pack(side="left")

        for label, act in [
            ("Start", "start"), ("Stop", "stop"), ("Restart", "restart"),
            ("Automatic", "automatic"), ("Delayed", "delayed"),
            ("Manual", "manual"), ("Disabled", "disabled")
        ]:
            ctk.CTkButton(bar, text=label, width=70, command=lambda a=act: self.bulk_services(a)).pack(side="right", padx=2)

        self.service_table = FilterableTable(
            p, ["Name", "DisplayName", "State", "StartMode", "StartName", "ProcessId", "Category", "Path", "Description"],
            [160, 240, 90, 100, 170, 80, 150, 520, 380],
            default_sort="DisplayName", category_field="Category"
        )
        self.service_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def bulk_services(self, action):
        rows = self.service_table.filtered
        eligible = [r for r in rows if r.get("Name") not in PROTECTED_SERVICE_NAMES and r.get("Category") != "Security"]
        if not eligible:
            return messagebox.showwarning("Services", "Current filter contains no eligible non-protected services.")
        label = action.title()
        if not messagebox.askyesno("Service Configuration", f"Apply '{label}' to {len(eligible)} eligible filtered service(s)?"):
            return
        done = 0
        for r in eligible:
            ok, _ = service_action(r.get("Name"), action)
            done += int(ok)
        self.set_status(f"Services {action}: {done}/{len(eligible)}")
        self.refresh_services()

    # ── 6. Startup ───────────────────────────────────────────────────────────
    def _build_startup(self):
        p = self.new_page("Startup")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)

        for text, action in [
            ("Enable Filtered", "enable"),
            ("Disable Filtered", "disable"),
            ("Delete Filtered", "delete")
        ]:
            ctk.CTkButton(
                bar, text=text, command=lambda a=action: self.bulk_startup(a),
                fg_color=THEME["danger"] if action == "delete" else None
            ).pack(side="left", padx=3)

        ctk.CTkLabel(bar, text="Delete creates automatic JSON backup. Inspect Registry & Folder items.",
                     text_color=THEME["text_muted"]).pack(side="left", padx=10)

        self.startup_table = FilterableTable(
            p, ["Scope", "Location", "Name", "Command", "Type", "Enabled"],
            [120, 320, 200, 780, 140, 90], default_sort="Name", category_field="Type"
        )
        self.startup_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def bulk_startup(self, action):
        rows = self.startup_table.filtered
        if not rows:
            return messagebox.showinfo("Startup", "No rows in the current filtered view.")
        title = {"enable": "Enable", "disable": "Disable", "delete": "Delete"}[action]
        if not messagebox.askyesno(f"{title} Startup", f"{title} {len(rows)} startup item(s)?\n(Automatic JSON backup is saved for deletion)"):
            return
        done = 0
        if action == "enable":
            for r in rows:
                done += int(enable_startup(r)[0])
        else:
            for r in rows:
                done += int(disable_startup(r)[0])
        self.set_status(f"Startup {action}: {done}/{len(rows)}")
        self.refresh_startup()

    # ── 7. Applications ──────────────────────────────────────────────────────
    def _build_apps(self):
        p = self.new_page("Applications")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(p, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        ctk.CTkButton(bar, text="Refresh Installed Apps", command=self.refresh_apps).pack(side="left")
        ctk.CTkButton(bar, text="Open Install Location", command=self.open_app_location).pack(side="left", padx=5)
        ctk.CTkButton(bar, text="Open Windows Apps Settings", command=self.open_app_settings).pack(side="left", padx=5)

        self.app_table = FilterableTable(
            p, ["Name", "Version", "Publisher", "InstallLocation", "UninstallString", "Type", "Scope"],
            [240, 120, 200, 520, 520, 90, 120], default_sort="Name", category_field="Type"
        )
        self.app_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def open_app_location(self):
        rows = self.app_table.selected_rows()
        if not rows:
            return messagebox.showinfo("Applications", "Please select an application.")
        path = norm(rows[0].get("InstallLocation"))
        if path and Path(path).exists():
            os.startfile(path)
        else:
            messagebox.showwarning("Applications", "Install directory is not directly available.")

    def open_app_settings(self):
        run_cmd(["explorer.exe", "ms-settings:appsfeatures"], timeout=10)

    # ── 8. Network ───────────────────────────────────────────────────────────
    def _build_network(self):
        p = self.new_page("Network")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        ctk.CTkButton(top, text="Refresh Network", command=self.refresh_network).pack(side="left")
        ctk.CTkLabel(top, text="Network Adapters & Active Established TCP Connections",
                     text_color=THEME["text_muted"]).pack(side="left", padx=10)

        body = ctk.CTkFrame(p, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, fg_color="transparent")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right = ctk.CTkFrame(body, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))

        self.adapter_table = FilterableTable(
            left, ["Name", "InterfaceDescription", "Status", "LinkSpeed", "MacAddress", "MediaType"],
            [130, 280, 90, 110, 140, 120], default_sort="Name", category_field="Status"
        )
        self.adapter_table.pack(fill="both", expand=True)

        self.tcp_table = FilterableTable(
            right, ["LocalAddress", "LocalPort", "RemoteAddress", "RemotePort", "State", "PID", "Process"],
            [140, 75, 180, 85, 95, 75, 170], default_sort="Process", category_field="State"
        )
        self.tcp_table.pack(fill="both", expand=True)

    # ── 9. Performance ───────────────────────────────────────────────────────
    def _build_performance(self):
        p = self.new_page("Performance")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)

        self.perf_labels = {}
        for key in ("CPU", "RAM", "NETWORK", "DISK"):
            var = tk.StringVar(value="—")
            self.perf_labels[key] = var
            f = ctk.CTkFrame(top, corner_radius=10, fg_color=THEME["bg_card"])
            f.pack(side="left", fill="x", expand=True, padx=4)
            ctk.CTkLabel(f, text=key, text_color=THEME["text_muted"], font=(FONT_FAMILY, 9, "bold")).pack(
                anchor="w", padx=12, pady=(8, 0)
            )
            ctk.CTkLabel(f, textvariable=var, font=(FONT_FAMILY, 15, "bold")).pack(
                anchor="w", padx=12, pady=(2, 8)
            )

        history = ctk.CTkFrame(p, corner_radius=12, fg_color=THEME["bg_card"])
        history.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        ctk.CTkLabel(history, text="Telemetry History", font=FONT_HEADING).pack(
            anchor="w", padx=14, pady=(12, 6)
        )
        self.perf_table = FilterableTable(
            history, ["Time", "CPU_%", "RAM_%", "NetRx_KB", "NetTx_KB"],
            [160, 90, 90, 130, 130], default_sort="Time"
        )
        self.perf_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def update_performance_loop(self):
        def sample_worker():
            sample = get_performance_sample()
            now = datetime.now().strftime("%H:%M:%S")
            self.after(0, lambda: self._apply_performance(sample, now))

        threading.Thread(target=sample_worker, daemon=True).start()
        self.after(5000, self.update_performance_loop)

    def _apply_performance(self, sample, now):
        cpu = sample.get("CPU", 0)
        ram = sample.get("RAM", 0)
        rx = sample.get("Rx", 0)
        tx = sample.get("Tx", 0)

        self.perf_labels["CPU"].set(f"{cpu} %")
        self.perf_labels["RAM"].set(f"{ram} %")
        self.perf_labels["NETWORK"].set(f"Rx {rx} KB / Tx {tx} KB")
        self.perf_labels["DISK"].set("Active")

        self.performance_history.append({
            "Time": now, "CPU_%": cpu, "RAM_%": ram,
            "NetRx_KB": rx, "NetTx_KB": tx
        })
        self.performance_history = self.performance_history[-120:]
        self.perf_table.set_data(list(reversed(self.performance_history)))

    # ── 10. Storage ──────────────────────────────────────────────────────────
    def _build_storage(self):
        p = self.new_page("Storage")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)
        ctk.CTkButton(top, text="Refresh Storage", command=self.refresh_drives).pack(side="left")
        ctk.CTkButton(top, text="Clean TEMP", command=lambda: self.run_storage_cleanup("temp")).pack(side="left", padx=5)
        ctk.CTkButton(top, text="Empty Recycle Bin", command=lambda: self.run_storage_cleanup("recycle")).pack(side="left", padx=5)
        ctk.CTkButton(
            top, text="DISM Component Cleanup", command=self.run_dism,
            fg_color="#805500", hover_color="#996600"
        ).pack(side="left", padx=5)

        self.storage_table = FilterableTable(
            p, ["DeviceID", "UsedGB", "FreeGB", "TotalGB", "FileSystem", "VolumeName"],
            [90, 110, 110, 110, 120, 250], default_sort="FreeGB"
        )
        self.storage_table.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def run_storage_cleanup(self, which):
        if which == "temp":
            d, s = cleanup_temp()
            messagebox.showinfo("TEMP Cleanup", f"Deleted: {d} items\nSkipped (locked): {s} items")
        else:
            ok = empty_recycle_bin()
            messagebox.showinfo("Recycle Bin", "Recycle Bin purged." if ok else "Cleanup failed.")
        self.refresh_drives()

    # ── 11. Maintenance ──────────────────────────────────────────────────────
    def _build_maintenance(self):
        p = self.new_page("Maintenance")
        box = ctk.CTkFrame(p, corner_radius=12, fg_color=THEME["bg_card"])
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="Safe System Maintenance", font=FONT_HEADING).pack(
            anchor="w", padx=16, pady=(16, 8)
        )
        for text, cmd in [
            ("Clean TEMP Cache", cleanup_temp),
            ("Flush DNS Resolver Cache", flush_dns),
            ("Restart Windows Explorer Shell", refresh_explorer),
            ("Empty Recycle Bin", empty_recycle_bin)
        ]:
            ctk.CTkButton(
                box, text=text, width=220,
                command=lambda f=cmd: self.run_maintenance_action(f)
            ).pack(anchor="w", padx=16, pady=5)

        adv = ctk.CTkFrame(p, corner_radius=12, fg_color=THEME["bg_card"])
        adv.pack(fill="x", padx=18, pady=(0, 18))
        ctk.CTkLabel(adv, text="Advanced Component Servicing", font=FONT_HEADING).pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        ctk.CTkLabel(adv, text="DISM Component Store Cleanup reduces WinSxS footprint. May take several minutes.",
                     text_color=THEME["text_muted"]).pack(anchor="w", padx=16, pady=4)
        ctk.CTkButton(
            adv, text="RUN DISM COMPONENT STORE CLEANUP", width=300,
            command=self.run_dism, fg_color="#805500", hover_color="#996600"
        ).pack(anchor="w", padx=16, pady=12)

    def run_maintenance_action(self, func):
        def work():
            res = func()
            self.after(0, lambda: messagebox.showinfo("Maintenance Result", str(res)))
        threading.Thread(target=work, daemon=True).start()

    def run_dism(self):
        if not messagebox.askyesno("DISM Cleanup", "Execute DISM StartComponentCleanup?\nThis process may take several minutes."):
            return
        def work():
            ok, text = component_cleanup()
            self.after(0, lambda: messagebox.showinfo("DISM Result", ("Completed" if ok else "Error") + "\n\n" + text[-1500:]))
        threading.Thread(target=work, daemon=True).start()

    def smart_optimize(self):
        if not messagebox.askyesno("Smart Optimize", "Execute conservative optimization?\n\n• Purge TEMP cache\n• Flush DNS resolver cache\n• Restart Explorer shell\n(No service disruption or forced process termination)"):
            return
        def work():
            cleanup_temp()
            flush_dns()
            refresh_explorer()
            self.after(0, self.refresh_all)
        threading.Thread(target=work, daemon=True).start()

    # ── 12. System ───────────────────────────────────────────────────────────
    def _build_system(self):
        p = self.new_page("System")
        body = ctk.CTkFrame(p, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=18)
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(body, corner_radius=12, fg_color=THEME["bg_card"])
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(left, text="Hardware & OS Profile", font=FONT_HEADING).pack(
            anchor="w", padx=16, pady=(16, 8)
        )
        self.system_text = tk.Text(
            left, bg=THEME["bg_card"], fg=THEME["text_main"],
            insertbackground=THEME["text_main"], bd=0, wrap="word", font=(FONT_FAMILY, 10)
        )
        self.system_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        right = ctk.CTkFrame(body, corner_radius=12, fg_color=THEME["bg_card"])
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(right, text="Storage Drive Distribution", font=FONT_HEADING).pack(
            anchor="w", padx=16, pady=(16, 8)
        )
        self.system_drive_table = FilterableTable(
            right, ["DeviceID", "UsedGB", "FreeGB", "TotalGB", "FileSystem", "VolumeName"],
            [90, 110, 110, 110, 120, 250], default_sort="FreeGB"
        )
        self.system_drive_table.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── 13. Reports ──────────────────────────────────────────────────────────
    def _build_reports(self):
        p = self.new_page("Reports")
        box = ctk.CTkFrame(p, corner_radius=12, fg_color=THEME["bg_card"])
        box.pack(fill="x", padx=18, pady=18)

        ctk.CTkLabel(box, text="Audit Reports & Data Export", font=FONT_HEADING).pack(
            anchor="w", padx=16, pady=(16, 4)
        )
        ctk.CTkLabel(box, text="Comprehensive JSON machine audit and per-module CSV logs.",
                     text_color=THEME["text_muted"]).pack(anchor="w", padx=16, pady=(0, 14))

        ctk.CTkButton(box, text="EXPORT FULL JSON SYSTEM AUDIT", command=self.export_audit).pack(anchor="w", padx=16, pady=5)
        ctk.CTkButton(box, text="OPEN REPORT & BACKUP FOLDER", command=lambda: os.startfile(APP_DIR)).pack(anchor="w", padx=16, pady=(5, 16))

    def export_audit(self):
        def work():
            data = {
                "generated": datetime.now().isoformat(),
                "administrator": is_admin(),
                "memory": get_memory(),
                "system": get_system_info(),
                "processes": get_processes(),
                "tasks": get_tasks(),
                "services": get_services(),
                "startup": get_startup(),
                "applications": get_installed_apps(),
                "network_adapters": get_network_adapters(),
                "tcp_connections": get_tcp_connections(),
                "drives": get_drives(),
                "config": CONFIG
            }
            out = REPORT_DIR / f"OptimusPrime_Audit_{datetime.now():%Y%m%d_%H%M%S}.json"
            out.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
            log(f"System audit generated: {out}")
            self.after(0, lambda: messagebox.showinfo("Audit Saved", f"Audit saved successfully:\n{out}"))

        threading.Thread(target=work, daemon=True).start()

    # ── 14. Log ──────────────────────────────────────────────────────────────
    def _build_log(self):
        p = self.new_page("Log")
        p.grid_rowconfigure(1, weight=1)
        p.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(p, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=18, pady=10)

        ctk.CTkButton(top, text="Refresh Log", command=self.refresh_log).pack(side="left")
        ctk.CTkButton(top, text="Clear Log", command=self.clear_log).pack(side="left", padx=6)
        ctk.CTkButton(top, text="Open App Folder", command=lambda: os.startfile(APP_DIR)).pack(side="right")

        from optimusprime.utils.constants import LOG_FILE
        self.log_file = LOG_FILE
        self.log_box = tk.Text(
            p, bg=THEME["bg_card"], fg=THEME["text_main"],
            insertbackground=THEME["text_main"], bd=0, wrap="none", font=("Consolas", 9)
        )
        self.log_box.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))

    def refresh_log(self):
        try:
            text = self.log_file.read_text(encoding="utf-8") if self.log_file.exists() else "No log records recorded."
        except Exception as exc:
            text = str(exc)
        self.log_box.delete("1.0", "end")
        self.log_box.insert("end", text)
        self.log_box.see("end")

    def clear_log(self):
        if messagebox.askyesno("Clear Log", "Purge persistent OPTIMUSPRIME activity log?"):
            try:
                self.log_file.unlink(missing_ok=True)
            except Exception:
                pass
            self.refresh_log()

    # ── Global Refresh & Data Hydration ──────────────────────────────────────
    def refresh_all(self):
        if self._is_refreshing:
            return
        self._is_refreshing = True
        self.set_status("Refreshing system state…")

        def worker():
            mem = get_memory()
            procs = get_processes()
            tsks = get_tasks()
            svcs = get_services()
            sups = get_startup()
            sys_info = get_system_info()
            drvs = get_drives()
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

            # Sidebar statistics
            admin = is_admin()
            self.sidebar_stats.configure(
                text=f"RAM {self.memory.get('UsedPct', '—')}%  •  {len(self.processes):,} procs\n{len(self.services):,} svcs  •  {len(self.tasks):,} tasks"
            )
            self.admin_label.configure(
                text="ADMINISTRATOR" if admin else "STANDARD USER",
                text_color=THEME["success"] if admin else THEME["warning"]
            )
            self.badge.configure(
                text="ADMIN" if admin else "STANDARD",
                text_color=THEME["success"] if admin else THEME["warning"]
            )
            self.set_status(f"Updated {datetime.now():%H:%M:%S}")
        finally:
            self._is_refreshing = False

        # Schedule next automatic refresh
        interval = max(3, int(CONFIG.get("refresh_seconds", 5))) * 1000
        self.after(interval, self.refresh_all)

    def update_dashboard(self):
        self.card_vars["RAM"].set(f"{fmt_gb(self.memory.get('UsedGB'))} / {fmt_gb(self.memory.get('TotalGB'))} GB\n{self.memory.get('UsedPct', '—')}%")
        self.card_vars["PROC"].set(f"{len(self.processes):,}")

        if self.processes:
            top = max(self.processes, key=lambda r: float(r.get("RAM_MB") or 0))
            self.card_vars["TOP"].set(f"{top.get('Name')}\n{fmt_mb(top.get('RAM_MB'))} MB")
            self.dashboard_table.set_data([
                {
                    "Name": r.get("Name"), "PID": r.get("PID"),
                    "RAM_MB": r.get("RAM_MB"), "CPU_s": r.get("CPU_s"),
                    "Owner": r.get("Owner")
                }
                for r in self.processes
            ])
        else:
            self.card_vars["TOP"].set("—")
            self.dashboard_table.set_data([])

        c_drive = next((d for d in self.drives if norm(d.get("DeviceID")).upper() == "C:"), None)
        self.card_vars["DISK"].set(f"{fmt_gb(c_drive.get('FreeGB'))} GB free" if c_drive else "—")

        own_task = next((t for t in self.tasks if t.get("TaskName") == TASK_NAME), None)
        self.card_vars["TASK"].set(norm(own_task.get("State")) if own_task else "Not Registered")

        self.dashboard_note.configure(
            text="Optimization Insights:\n• App Sleep suspends background browser/app instances.\n• Filter views before executing batch operations.\n• Core Windows and Security services are shielded.\n• Backups are automatically generated before deletions."
        )

    def apply_system_text(self):
        self.system_text.delete("1.0", "end")
        for k, v in self.system.items():
            self.system_text.insert("end", f"{k}: {v}\n")

    def refresh_processes(self):
        threading.Thread(target=lambda: self._apply_process(get_processes()), daemon=True).start()

    def _apply_process(self, rows):
        self.processes = list(rows or [])
        self.process_table.set_data(self.processes)
        self.refresh_sleep_table()

    def refresh_tasks(self):
        threading.Thread(target=lambda: self._apply_tasks(get_tasks()), daemon=True).start()

    def _apply_tasks(self, rows):
        self.tasks = list(rows or [])
        self.task_table.set_data(self.tasks)

    def refresh_services(self):
        threading.Thread(target=lambda: self._apply_services(get_services()), daemon=True).start()

    def _apply_services(self, rows):
        self.services = list(rows or [])
        self.service_table.set_data(self.services)

    def refresh_startup(self):
        threading.Thread(target=lambda: self._apply_startup(get_startup()), daemon=True).start()

    def _apply_startup(self, rows):
        self.startups = list(rows or [])
        self.startup_table.set_data(self.startups)

    def refresh_apps(self):
        threading.Thread(target=lambda: self._apply_apps(get_installed_apps()), daemon=True).start()

    def _apply_apps(self, rows):
        self.apps = list(rows or [])
        self.app_table.set_data(self.apps)

    def refresh_network(self):
        threading.Thread(target=lambda: self._apply_network(get_network_adapters(), get_tcp_connections()), daemon=True).start()

    def _apply_network(self, adapters, conns):
        self.adapters = list(adapters or [])
        self.connections = list(conns or [])
        self.adapter_table.set_data(self.adapters)
        self.tcp_table.set_data(self.connections)

    def refresh_drives(self):
        threading.Thread(target=lambda: self._apply_drives(get_drives()), daemon=True).start()

    def _apply_drives(self, rows):
        self.drives = list(rows or [])
        self.storage_table.set_data(self.drives)
        self.system_drive_table.set_data(self.drives)

    def restart_elevated(self):
        if elevate_current_script():
            self.destroy()
