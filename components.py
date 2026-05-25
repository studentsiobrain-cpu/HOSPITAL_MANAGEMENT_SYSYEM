from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable


class ScrollFrame(ttk.Frame):
    def __init__(self, parent, **kwargs) -> None:
        super().__init__(parent, **kwargs)
        self.canvas = tk.Canvas(self, highlightthickness=0, bg=self.winfo_toplevel().cget("bg"))
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas)
        self.window_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

    def _on_frame_configure(self, _event) -> None:
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event) -> None:
        self.canvas.itemconfigure(self.window_id, width=event.width)


class MetricCard(ttk.Frame):
    def __init__(self, parent, title: str, value: str, caption: str = "") -> None:
        super().__init__(parent, style="Panel.TFrame", padding=16)
        ttk.Label(self, text=title, style="CardTitle.TLabel").pack(anchor="w")
        ttk.Label(self, text=value, style="CardValue.TLabel").pack(anchor="w", pady=(5, 0))
        if caption:
            ttk.Label(self, text=caption, style="Muted.TLabel").pack(anchor="w", pady=(2, 0))


class DataTable(ttk.Frame):
    def __init__(self, parent, columns: list[str], on_select: Callable[[dict], None] | None = None) -> None:
        super().__init__(parent)
        self.columns = columns
        self.on_select = on_select
        self.tree = ttk.Treeview(self, columns=columns, show="headings", selectmode="browse")
        y_scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(self, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, minwidth=90, width=140, stretch=True)
        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        if on_select:
            self.tree.bind("<<TreeviewSelect>>", self._selected)

    def set_rows(self, rows) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            values = [row[col] if hasattr(row, "keys") and col in row.keys() else "" for col in self.columns]
            self.tree.insert("", "end", values=values)

    def selected_id(self) -> int | None:
        selected = self.tree.selection()
        if not selected:
            return None
        values = self.tree.item(selected[0], "values")
        return int(values[0]) if values else None

    def as_rows(self) -> list[tuple]:
        return [tuple(self.tree.item(item, "values")) for item in self.tree.get_children()]

    def _selected(self, _event) -> None:
        selected = self.tree.selection()
        if selected and self.on_select:
            values = self.tree.item(selected[0], "values")
            self.on_select(dict(zip(self.columns, values)))


class FormDialog(tk.Toplevel):
    def __init__(self, parent, title: str, fields: list[dict], on_submit: Callable[[dict], None]) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry("560x620")
        self.transient(parent)
        self.grab_set()
        self.on_submit = on_submit
        self.inputs: dict[str, tk.Variable | tk.Text] = {}
        frame = ScrollFrame(self, padding=14)
        frame.pack(fill="both", expand=True)
        for idx, field in enumerate(fields):
            ttk.Label(frame.inner, text=field["label"]).grid(row=idx * 2, column=0, sticky="w", pady=(8, 2))
            kind = field.get("kind", "entry")
            name = field["name"]
            if kind == "combo":
                var = tk.StringVar(value=field.get("default", ""))
                widget = ttk.Combobox(frame.inner, textvariable=var, values=field.get("values", []), state=field.get("state", "normal"))
                self.inputs[name] = var
            elif kind == "text":
                widget = tk.Text(frame.inner, height=4, wrap="word")
                if field.get("default"):
                    widget.insert("1.0", field["default"])
                self.inputs[name] = widget
            else:
                var = tk.StringVar(value=field.get("default", ""))
                widget = ttk.Entry(frame.inner, textvariable=var, show=field.get("show", ""))
                self.inputs[name] = var
            widget.grid(row=idx * 2 + 1, column=0, sticky="ew", pady=(0, 4))
        frame.inner.columnconfigure(0, weight=1)
        actions = ttk.Frame(self, padding=14)
        actions.pack(fill="x")
        ttk.Button(actions, text="Cancel", command=self.destroy).pack(side="right", padx=(8, 0))
        ttk.Button(actions, text="Save", style="Accent.TButton", command=self._submit).pack(side="right")

    def _submit(self) -> None:
        values = {}
        for key, widget in self.inputs.items():
            if isinstance(widget, tk.Text):
                values[key] = widget.get("1.0", "end").strip()
            else:
                values[key] = widget.get().strip()
        try:
            self.on_submit(values)
        except Exception as exc:
            messagebox.showerror("Unable to save", str(exc), parent=self)
            return
        self.destroy()


def selected_combo_id(value: str) -> int:
    return int(value.split(" - ", 1)[0])
