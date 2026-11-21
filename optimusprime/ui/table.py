# -*- coding: utf-8 -*-
"""
OPTIMUSPRIME Reusable High-Density Filterable Table Component
"""
import csv
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from optimusprime.utils.helpers import norm
from optimusprime.utils.logger import log
from optimusprime.ui.theme import THEME, FONT_FAMILY


class FilterableTable(ctk.CTkFrame):
    """Universal high-density table with real-time multi-column search, filtering, sorting and CSV export."""

    def __init__(self, master, columns, widths=None, default_sort=None,
                 category_field=None, category_label="Category", **kwargs):
        super().__init__(master, fg_color=THEME["bg_card"], corner_radius=12, **kwargs)
        self.columns = list(columns)
        self.widths = widths or [150] * len(columns)
        self.default_sort = default_sort or self.columns[0]
        self.sort_column = self.default_sort
        self.sort_reverse = False
        self.category_field = category_field
        self.category_label = category_label
        self.data = []
        self.filtered = []
        self.visible = {c: True for c in self.columns}

        # ── Toolbar ──────────────────────────────────────────────────────────
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 6))
        top.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Search", font=(FONT_FAMILY, 11, "bold")).grid(row=0, column=0, padx=(0, 6))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.apply_filters())
        ctk.CTkEntry(
            top, textvariable=self.search_var, width=200,
            placeholder_text="Search all columns…"
        ).grid(row=0, column=1, sticky="ew", padx=4)

        self.column_var = tk.StringVar(value="All Columns")
        self.column_box = ctk.CTkComboBox(
            top, values=["All Columns"] + self.columns,
            variable=self.column_var, width=140, state="readonly",
            command=lambda *_: self.apply_filters()
        )
        self.column_box.grid(row=0, column=2, padx=4)

        self.operator_var = tk.StringVar(value="Contains")
        self.operator_box = ctk.CTkComboBox(
            top,
            values=["Contains", "Equals", "Starts With", "Ends With", ">", ">=", "<", "<="],
            variable=self.operator_var, width=115, state="readonly",
            command=lambda *_: self.apply_filters()
        )
        self.operator_box.grid(row=0, column=3, padx=4)

        self.value_var = tk.StringVar()
        self.value_var.trace_add("write", lambda *_: self.apply_filters())
        ctk.CTkEntry(
            top, textvariable=self.value_var, width=120,
            placeholder_text="Value…"
        ).grid(row=0, column=4, padx=4)

        self.category_box = None
        self.category_var = tk.StringVar(value="All")
        if category_field:
            self.category_box = ctk.CTkComboBox(
                top, values=["All"], variable=self.category_var,
                width=140, state="readonly", command=lambda *_: self.apply_filters()
            )
            self.category_box.grid(row=0, column=5, padx=4)

        ctk.CTkButton(top, text="Clear", width=60, command=self.clear_filters).grid(row=0, column=6, padx=4)
        ctk.CTkButton(top, text="Columns", width=70, command=self.column_menu).grid(row=0, column=7, padx=4)
        ctk.CTkButton(top, text="Copy", width=55, command=self.copy_selected).grid(row=0, column=8, padx=4)
        ctk.CTkButton(top, text="CSV", width=55, command=self.export_csv).grid(row=0, column=9, padx=(4, 0))

        # ── Treeview Body ────────────────────────────────────────────────────
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 4))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "OptimusPrime.Treeview",
            background=THEME["bg_tree"],
            fieldbackground=THEME["bg_tree"],
            foreground=THEME["text_main"],
            rowheight=28,
            borderwidth=0,
            font=(FONT_FAMILY, 9)
        )
        style.map(
            "OptimusPrime.Treeview",
            background=[("selected", THEME["primary"])],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "OptimusPrime.Treeview.Heading",
            background=THEME["bg_heading"],
            foreground="#b7c2d4",
            relief="flat",
            font=(FONT_FAMILY, 9, "bold")
        )

        self.tree = ttk.Treeview(
            body, columns=self.columns, show="headings",
            selectmode="extended", style="OptimusPrime.Treeview"
        )
        for col, width in zip(self.columns, self.widths):
            self.tree.heading(col, text=col, command=lambda c=col: self.sort_by(c))
            self.tree.column(col, width=width, minwidth=50, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")

        y_scroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        # ── Status Footer ────────────────────────────────────────────────────
        self.info = ctk.CTkLabel(self, text="0 rows", text_color=THEME["text_muted"], font=(FONT_FAMILY, 9))
        self.info.pack(anchor="w", padx=12, pady=(0, 6))

    def set_data(self, rows):
        """Update table data source and refresh view."""
        self.data = list(rows or [])
        if self.category_field and self.category_box:
            values = sorted({norm(r.get(self.category_field)) for r in self.data if norm(r.get(self.category_field))})
            options = ["All"] + values
            current = self.category_var.get()
            self.category_box.configure(values=options)
            self.category_var.set(current if current in options else "All")
        self.apply_filters()

    def _matches(self, row, col, op, target):
        text = (" | ".join(norm(row.get(c)) for c in self.columns)
                if col == "All Columns" else norm(row.get(col)))
        a, b = text.lower(), norm(target).lower()
        if op == "Contains":
            return b in a
        if op == "Equals":
            return a == b
        if op == "Starts With":
            return a.startswith(b)
        if op == "Ends With":
            return a.endswith(b)
        try:
            na = float(text.replace(",", "").replace("%", ""))
            nb = float(norm(target).replace(",", "").replace("%", ""))
        except Exception:
            na, nb = a, b
        return {">": na > nb, ">=": na >= nb, "<": na < nb, "<=": na <= nb}.get(op, False)

    def apply_filters(self):
        """Filter and sort rows based on active toolbar settings."""
        search = self.search_var.get().strip().lower()
        col = self.column_var.get()
        op = self.operator_var.get()
        val = self.value_var.get().strip()
        category = self.category_var.get()

        rows = []
        for row in self.data:
            if self.category_field and category != "All" and norm(row.get(self.category_field)) != category:
                continue
            if search:
                all_text = " | ".join(norm(row.get(c)) for c in self.columns).lower()
                if search not in all_text:
                    continue
            if val and not self._matches(row, col, op, val):
                continue
            rows.append(row)

        def sort_key(row):
            value = norm(row.get(self.sort_column))
            try:
                clean_num = value.replace(",", "").replace("%", "").strip()
                return (0, float(clean_num))
            except Exception:
                return (1, value.lower())

        rows.sort(key=sort_key, reverse=self.sort_reverse)
        self.filtered = rows
        self.render()

    def render(self):
        """Draw filtered rows into treeview."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        display = [c for c in self.columns if self.visible.get(c, True)]
        self.tree["displaycolumns"] = display
        for col, width in zip(self.columns, self.widths):
            self.tree.column(col, width=width if self.visible.get(col, True) else 0)
        for idx, row in enumerate(self.filtered):
            self.tree.insert("", "end", iid=str(idx), values=[norm(row.get(c)) for c in self.columns])
        arrow = "▼" if self.sort_reverse else "▲"
        self.info.configure(text=f"{len(self.filtered):,} / {len(self.data):,} rows   •   Sorted by {self.sort_column} {arrow}")

    def sort_by(self, column):
        """Toggle column sort direction."""
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column, self.sort_reverse = column, False
        self.apply_filters()

    def clear_filters(self):
        """Reset search and filter fields."""
        self.search_var.set("")
        self.column_var.set("All Columns")
        self.operator_var.set("Contains")
        self.value_var.set("")
        self.category_var.set("All")
        self.apply_filters()

    def selected_rows(self) -> list:
        """Return currently highlighted row dictionaries."""
        output = []
        for iid in self.tree.selection():
            try:
                output.append(self.filtered[int(iid)])
            except Exception:
                pass
        return output

    def column_menu(self):
        """Display popup to toggle visible columns."""
        popup = ctk.CTkToplevel(self)
        popup.title("Column Visibility")
        popup.geometry("320x460")
        popup.transient(self.winfo_toplevel())
        ctk.CTkLabel(popup, text="Select Visible Columns", font=(FONT_FAMILY, 14, "bold")).pack(pady=12)
        body = ctk.CTkScrollableFrame(popup)
        body.pack(fill="both", expand=True, padx=12, pady=5)
        variables = {}
        for col in self.columns:
            var = tk.BooleanVar(value=self.visible.get(col, True))
            variables[col] = var
            ctk.CTkCheckBox(body, text=col, variable=var).pack(anchor="w", pady=4)

        def apply():
            self.visible.update({c: v.get() for c, v in variables.items()})
            if not any(self.visible.values()):
                self.visible[self.columns[0]] = True
            self.render()
            popup.destroy()

        ctk.CTkButton(popup, text="Apply", command=apply).pack(pady=12)

    def copy_selected(self):
        """Copy selected rows to clipboard as tab-delimited text."""
        rows = self.selected_rows()
        if not rows:
            return
        text = "\n".join("\t".join(norm(r.get(c)) for c in self.columns) for r in rows)
        self.clipboard_clear()
        self.clipboard_append(text)
        self.info.configure(text=f"Copied {len(rows)} selected row(s) to clipboard")

    def export_csv(self):
        """Export current filtered view to CSV file."""
        path = filedialog.asksaveasfilename(
            title="Export Current Filtered View", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=self.columns)
                writer.writeheader()
                writer.writerows(self.filtered)
            self.info.configure(text=f"Exported {len(self.filtered):,} rows to {path}")
            log(f"CSV exported successfully: {path}")
        except Exception as exc:
            messagebox.showerror("Export CSV", str(exc))
