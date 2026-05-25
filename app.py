from __future__ import annotations

import logging
import tkinter as tk
from tkinter import messagebox, ttk

from .auth import CurrentUser
from .config import APP_NAME, ensure_directories
from .database import Database
from .seed import seed_database
from .services import AuthService, HospitalService, ValidationError
from .ui.modules import (
    AdminToolsModule,
    AppointmentsModule,
    BillingModule,
    DashboardModule,
    DoctorsModule,
    EmployeesModule,
    InventoryModule,
    LaboratoryModule,
    PatientsModule,
    SurgeriesModule,
    WardsModule,
)
from .ui.styles import ThemeManager
from .utils import configure_logging


MODULES = [
    ("dashboard", "Dashboard", DashboardModule),
    ("patients", "Patients", PatientsModule),
    ("doctors", "Doctors", DoctorsModule),
    ("appointments", "Appointments", AppointmentsModule),
    ("laboratory", "Laboratory", LaboratoryModule),
    ("billing", "Billing", BillingModule),
    ("wards", "Wards & Beds", WardsModule),
    ("inventory", "Inventory", InventoryModule),
    ("employees", "Employees", EmployeesModule),
    ("surgeries", "Surgeries", SurgeriesModule),
    ("admin", "Admin Tools", AdminToolsModule),
]


class LoginWindow(ttk.Frame):
    def __init__(self, root: tk.Tk, auth: AuthService, on_success) -> None:
        super().__init__(root, padding=32)
        self.root = root
        self.auth = auth
        self.on_success = on_success
        self.pack(fill="both", expand=True)
        panel = ttk.Frame(self, style="Panel.TFrame", padding=28)
        panel.place(relx=0.5, rely=0.5, anchor="center", width=430)
        ttk.Label(panel, text=APP_NAME, style="Title.TLabel").pack(anchor="w")
        ttk.Label(panel, text="Secure hospital ERP login").pack(anchor="w", pady=(4, 18))
        self.username = tk.StringVar(value="admin")
        self.password = tk.StringVar(value="admin123")
        ttk.Label(panel, text="Username", style="Panel.TLabel").pack(anchor="w")
        ttk.Entry(panel, textvariable=self.username).pack(fill="x", pady=(2, 10))
        ttk.Label(panel, text="Password", style="Panel.TLabel").pack(anchor="w")
        password_entry = ttk.Entry(panel, textvariable=self.password, show="*")
        password_entry.pack(fill="x", pady=(2, 18))
        ttk.Button(panel, text="Login", style="Accent.TButton", command=self.login).pack(fill="x")
        ttk.Label(
            panel,
            text="Try admin/admin123, doctor/doctor123, reception/reception123, lab/lab123.",
            style="Muted.TLabel",
            wraplength=360,
        ).pack(anchor="w", pady=(16, 0))
        password_entry.bind("<Return>", lambda _event: self.login())

    def login(self) -> None:
        try:
            user = self.auth.login(self.username.get(), self.password.get())
        except ValidationError as exc:
            messagebox.showerror("Login failed", str(exc), parent=self)
            return
        self.destroy()
        self.on_success(user)


class HospitalApp:
    def __init__(self) -> None:
        ensure_directories()
        configure_logging()
        self.db = Database()
        seed_database(self.db)
        self.root = tk.Tk()
        self.root.title(APP_NAME)
        self.root.geometry("1380x820")
        self.root.minsize(1100, 680)
        self.theme = ThemeManager(self.root)
        self.theme.apply("light")
        self.auth = AuthService(self.db)
        self.user: CurrentUser | None = None
        LoginWindow(self.root, self.auth, self.start_main)

    def start_main(self, user: CurrentUser) -> None:
        self.user = user
        self.service = HospitalService(self.db, user)
        self.root.title(f"{APP_NAME} - {user.full_name} ({user.role})")
        self.layout = ttk.Frame(self.root)
        self.layout.pack(fill="both", expand=True)
        self.sidebar = ttk.Frame(self.layout, style="Sidebar.TFrame", width=220)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self.content = ttk.Frame(self.layout)
        self.content.pack(side="left", fill="both", expand=True)
        self._build_sidebar()
        self.open_module("dashboard")

    def _build_sidebar(self) -> None:
        ttk.Label(self.sidebar, text="AsterPrime HMS", style="Sidebar.TLabel").pack(fill="x", padx=16, pady=(18, 4))
        ttk.Label(self.sidebar, text=f"{self.user.role}", style="Sidebar.TLabel").pack(fill="x", padx=16, pady=(0, 14))
        for key, label, _klass in MODULES:
            if key == "admin" and self.user.role != "Admin":
                continue
            permission = key
            if self.user and self.user.can(permission):
                ttk.Button(self.sidebar, text=label, style="Nav.TButton", command=lambda k=key: self.open_module(k)).pack(fill="x", padx=10, pady=2)
        ttk.Frame(self.sidebar, style="Sidebar.TFrame").pack(fill="both", expand=True)
        ttk.Button(self.sidebar, text="Toggle Theme", style="Nav.TButton", command=self.toggle_theme).pack(fill="x", padx=10, pady=2)
        ttk.Button(self.sidebar, text="Logout", style="Nav.TButton", command=self.logout).pack(fill="x", padx=10, pady=(2, 14))

    def open_module(self, key: str) -> None:
        for child in self.content.winfo_children():
            child.destroy()
        module_class = next((klass for module_key, _label, klass in MODULES if module_key == key), DashboardModule)
        try:
            module = module_class(self.content, self.service)
            module.pack(fill="both", expand=True)
        except Exception as exc:
            logging.exception("Module failed: %s", key)
            messagebox.showerror("Module error", str(exc), parent=self.root)

    def toggle_theme(self) -> None:
        self.theme.apply("dark" if self.theme.theme_name == "light" else "light")

    def logout(self) -> None:
        if messagebox.askyesno("Logout", "End this session?"):
            self.layout.destroy()
            self.user = None
            LoginWindow(self.root, self.auth, self.start_main)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    HospitalApp().run()
