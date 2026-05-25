import tkinter as tk
from tkinter import ttk

from hospital_erp.config import THEMES


class ThemeManager:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.style = ttk.Style(root)
        self.theme_name = "light"

    @property
    def colors(self) -> dict[str, str]:
        return THEMES[self.theme_name]

    def apply(self, theme_name: str = "light") -> None:
        self.theme_name = theme_name
        colors = self.colors
        self.style.theme_use("clam")
        self.root.configure(bg=colors["bg"])
        self.style.configure(".", font=("Segoe UI", 10), background=colors["bg"], foreground=colors["text"])
        self.style.configure("TFrame", background=colors["bg"])
        self.style.configure("Panel.TFrame", background=colors["panel"], relief="flat")
        self.style.configure("Sidebar.TFrame", background=colors["sidebar"])
        self.style.configure("TLabel", background=colors["bg"], foreground=colors["text"])
        self.style.configure("Panel.TLabel", background=colors["panel"], foreground=colors["text"])
        self.style.configure("Muted.TLabel", background=colors["panel"], foreground=colors["muted"])
        self.style.configure("Title.TLabel", font=("Segoe UI Semibold", 18), background=colors["bg"], foreground=colors["text"])
        self.style.configure("CardTitle.TLabel", font=("Segoe UI Semibold", 10), background=colors["panel"], foreground=colors["muted"])
        self.style.configure("CardValue.TLabel", font=("Segoe UI Semibold", 20), background=colors["panel"], foreground=colors["text"])
        self.style.configure("Sidebar.TLabel", background=colors["sidebar"], foreground="#ffffff", font=("Segoe UI Semibold", 13))
        self.style.configure("TButton", padding=(10, 7), borderwidth=0)
        self.style.configure("Accent.TButton", background=colors["accent"], foreground="#ffffff")
        self.style.map("Accent.TButton", background=[("active", colors["sidebar_active"])])
        self.style.configure("Nav.TButton", anchor="w", padding=(14, 10), background=colors["sidebar"], foreground="#ffffff")
        self.style.map("Nav.TButton", background=[("active", colors["sidebar_active"])])
        self.style.configure("Treeview", rowheight=30, bordercolor=colors["border"], fieldbackground=colors["panel"], background=colors["panel"], foreground=colors["text"])
        self.style.configure("Treeview.Heading", font=("Segoe UI Semibold", 10), background=colors["border"], foreground=colors["text"])
        self.style.configure("TNotebook", background=colors["bg"], borderwidth=0)
        self.style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI Semibold", 10))
        self.style.configure("TEntry", padding=6)
        self.style.configure("TCombobox", padding=6)
