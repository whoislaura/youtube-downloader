import os
from pathlib import Path
import subprocess
import sys
from typing import Callable
import customtkinter as ctk

from src.config import THEME


def open_folder(path: str) -> None:
    folder = str(Path(path).resolve())
    if sys.platform == "win32":
        os.startfile(folder)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", folder])
    else:
        subprocess.Popen(["xdg-open", folder])


class QueueItemCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        task_id: str,
        title: str,
        badge: str,
        output_dir: str,
        on_cancel: Callable[[str], None],
    ):
        super().__init__(
            master,
            fg_color=THEME["bg_input"],
            corner_radius=8,
            border_width=1,
            border_color=THEME["border"],
        )
        self.task_id = task_id
        self.output_dir = output_dir
        self.on_cancel = on_cancel

        self.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(10, 4))
        top.grid_columnconfigure(0, weight=1)

        self.title_lbl = ctk.CTkLabel(
            top,
            text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME["text_primary"],
            anchor="w",
        )
        self.title_lbl.grid(row=0, column=0, sticky="ew", padx=(0, 8))

        self.badge_lbl = ctk.CTkLabel(
            top,
            text=badge,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=THEME["bg_elevated"],
            text_color=THEME["text_secondary"],
            corner_radius=6,
            padx=8,
            pady=2,
        )
        self.badge_lbl.grid(row=0, column=1, sticky="e")

        self.progress = ctk.CTkProgressBar(
            self,
            fg_color=THEME["bg_elevated"],
            progress_color=THEME["accent"],
            height=8,
            corner_radius=4,
        )
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=12, pady=(4, 4))

        self.action_btn = ctk.CTkButton(
            self,
            text="Cancelar",
            width=95,
            height=26,
            fg_color=THEME["bg_elevated"],
            hover_color=THEME["danger"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=12),
            command=self._handle_cancel,
        )
        self.action_btn.grid(row=1, column=1, rowspan=2, padx=(4, 12), pady=(2, 8))

        self.status_lbl = ctk.CTkLabel(
            self,
            text="En cola...",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        self.status_lbl.grid(row=2, column=0, sticky="w", padx=12, pady=(0, 8))

    def _handle_cancel(self) -> None:
        self.action_btn.configure(state="disabled", text="Cancelando...")
        self.on_cancel(self.task_id)

    def update_progress(self, pct: float, speed: str, eta: str, stage: str) -> None:
        self.progress.set(pct)
        pct_num = int(pct * 100)
        details = f"{ stage } {pct_num}%"
        if speed and speed != "-- MB/s":
            details += f" • {speed}"
        if eta and eta != "--:--":
            details += f" • ETA {eta}"
        self.status_lbl.configure(text=details, text_color=THEME["text_secondary"])

    def mark_completed(self, output_dir: str) -> None:
        self.output_dir = output_dir
        self.progress.set(1.0)
        self.progress.configure(progress_color=THEME["success"])
        self.status_lbl.configure(text="Completado", text_color=THEME["success"])
        self.action_btn.configure(
            state="normal",
            text="Abrir carpeta",
            fg_color=THEME["success"],
            hover_color=THEME["success_hover"],
            command=lambda: open_folder(self.output_dir),
        )

    def mark_error(self, message: str, cancelled: bool) -> None:
        self.progress.configure(progress_color=THEME["danger"])
        label = "Descarga cancelada" if cancelled else f"Error: {message[:80]}"
        self.status_lbl.configure(text=label, text_color=THEME["danger"])
        self.action_btn.configure(state="disabled", text="Cancelado" if cancelled else "Falló")


class QueuePanel(ctk.CTkFrame):
    def __init__(self, master, on_cancel: Callable[[str], None]):
        super().__init__(
            master,
            fg_color=THEME["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        self.on_cancel = on_cancel
        self.cards: dict[str, QueueItemCard] = {}

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 4))

        self.header_lbl = ctk.CTkLabel(
            header,
            text="Cola de descargas (0)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_primary"],
        )
        self.header_lbl.pack(side="left")

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.empty_lbl = ctk.CTkLabel(
            self.scroll,
            text="No hay descargas activas. Analiza un video para comenzar.",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"],
        )
        self.empty_lbl.pack(pady=36)

    def add_item(self, task_id: str, title: str, badge: str, output_dir: str) -> None:
        if self.empty_lbl.winfo_exists():
            self.empty_lbl.pack_forget()

        card = QueueItemCard(self.scroll, task_id, title, badge, output_dir, self.on_cancel)
        card.pack(fill="x", padx=4, pady=5)
        self.cards[task_id] = card
        self.header_lbl.configure(text=f"Cola de descargas ({len(self.cards)})")

    def update_progress(self, task_id: str, pct: float, speed: str, eta: str, stage: str) -> None:
        card = self.cards.get(task_id)
        if card:
            card.update_progress(pct, speed, eta, stage)

    def mark_completed(self, task_id: str, output_dir: str) -> None:
        card = self.cards.get(task_id)
        if card:
            card.mark_completed(output_dir)

    def mark_error(self, task_id: str, message: str, cancelled: bool) -> None:
        card = self.cards.get(task_id)
        if card:
            card.mark_error(message, cancelled)
