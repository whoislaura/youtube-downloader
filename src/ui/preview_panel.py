from io import BytesIO
import threading
from tkinter import filedialog
from typing import Callable
import customtkinter as ctk
from PIL import Image
import requests

from src.config import (
    AUDIO_FORMATS,
    AUDIO_QUALITIES,
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_RESOLUTIONS,
    THEME,
    VIDEO_FORMATS,
)
from src.core.analyzer import MediaInfo, VideoItem


class PlaylistSelectorDialog(ctk.CTkToplevel):
    def __init__(self, master, entries: list[VideoItem], selected_indices: set[int], on_save: Callable[[set[int]], None]):
        super().__init__(master)
        self.title("Seleccionar videos de la playlist")
        self.geometry("560x440")
        self.configure(fg_color=THEME["bg_main"])
        self.transient(master)
        self.grab_set()

        self.entries = entries
        self.on_save = on_save
        self.vars: list[ctk.BooleanVar] = []

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            header,
            text=f"Videos en la lista ({len(entries)})",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(side="left")

        ctk.CTkButton(
            header,
            text="Ninguno",
            width=75,
            height=28,
            fg_color=THEME["bg_elevated"],
            hover_color=THEME["border"],
            command=lambda: self._set_all(False),
        ).pack(side="right", padx=(6, 0))

        ctk.CTkButton(
            header,
            text="Todos",
            width=75,
            height=28,
            fg_color=THEME["bg_elevated"],
            hover_color=THEME["border"],
            command=lambda: self._set_all(True),
        ).pack(side="right")

        scroll = ctk.CTkScrollableFrame(
            self,
            fg_color=THEME["bg_card"],
            border_width=1,
            border_color=THEME["border"],
            corner_radius=10,
        )
        scroll.pack(fill="both", expand=True, padx=16, pady=6)

        for idx, item in enumerate(entries):
            var = ctk.BooleanVar(value=(idx in selected_indices))
            self.vars.append(var)
            cb = ctk.CTkCheckBox(
                scroll,
                text=f"{idx + 1}. {item.title}  ({item.duration})",
                variable=var,
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                text_color=THEME["text_primary"],
            )
            cb.pack(anchor="w", padx=10, pady=5)

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=16, pady=(8, 14))

        ctk.CTkButton(
            footer,
            text="Confirmar selección",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            height=36,
            font=ctk.CTkFont(weight="bold"),
            command=self._confirm,
        ).pack(side="right")

    def _set_all(self, state: bool) -> None:
        for var in self.vars:
            var.set(state)

    def _confirm(self) -> None:
        chosen = {idx for idx, var in enumerate(self.vars) if var.get()}
        self.on_save(chosen)
        self.destroy()


class PreviewPanel(ctk.CTkFrame):
    def __init__(self, master, on_enqueue: Callable[[list[VideoItem], str, str, str, str], None]):
        super().__init__(
            master,
            fg_color=THEME["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        self.on_enqueue = on_enqueue
        self.current_media: MediaInfo | None = None
        self.selected_indices: set[int] = set()
        self.output_dir = DEFAULT_DOWNLOAD_DIR

        self.grid_columnconfigure(0, weight=5)
        self.grid_columnconfigure(1, weight=6)

        # Left side: Thumbnail + Metadata
        self.left_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)

        self.thumb_label = ctk.CTkLabel(
            self.left_frame,
            text="Vista previa\ndel video",
            width=240,
            height=135,
            fg_color=THEME["bg_input"],
            corner_radius=8,
            text_color=THEME["text_muted"],
            font=ctk.CTkFont(size=13),
        )
        self.thumb_label.pack(anchor="w", pady=(0, 10))

        self.title_label = ctk.CTkLabel(
            self.left_frame,
            text="Pega un enlace de YouTube y presiona Analizar",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=THEME["text_primary"],
            justify="left",
            anchor="w",
            wraplength=310,
        )
        self.title_label.pack(fill="x", pady=(0, 4))

        self.meta_label = ctk.CTkLabel(
            self.left_frame,
            text="Canal • Duración",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
            justify="left",
            anchor="w",
        )
        self.meta_label.pack(fill="x")

        self.playlist_btn = ctk.CTkButton(
            self.left_frame,
            text="Seleccionar videos",
            height=28,
            fg_color=THEME["bg_elevated"],
            hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._open_playlist_selector,
        )

        # Right side: Format & Quality Controls
        self.right_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(4, 16), pady=16)
        self.right_frame.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            self.right_frame,
            text="Tipo de descarga",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))

        self.mode_switch = ctk.CTkSegmentedButton(
            self.right_frame,
            values=["Video", "Solo Audio"],
            selected_color=THEME["accent"],
            selected_hover_color=THEME["accent_hover"],
            unselected_color=THEME["bg_input"],
            unselected_hover_color=THEME["bg_elevated"],
            text_color=THEME["text_primary"],
            command=self._on_mode_change,
        )
        self.mode_switch.set("Video")
        self.mode_switch.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        ctk.CTkLabel(
            self.right_frame,
            text="Formato",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        ).grid(row=2, column=0, sticky="w", padx=(0, 6), pady=(0, 4))

        self.quality_header = ctk.CTkLabel(
            self.right_frame,
            text="Resolución",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        )
        self.quality_header.grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(0, 4))

        self.format_menu = ctk.CTkOptionMenu(
            self.right_frame,
            values=[f.upper() for f in VIDEO_FORMATS],
            fg_color=THEME["bg_input"],
            button_color=THEME["bg_elevated"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["bg_card"],
            text_color=THEME["text_primary"],
        )
        self.format_menu.set("MP4")
        self.format_menu.grid(row=3, column=0, sticky="ew", padx=(0, 6), pady=(0, 12))

        self.quality_menu = ctk.CTkOptionMenu(
            self.right_frame,
            values=DEFAULT_RESOLUTIONS,
            fg_color=THEME["bg_input"],
            button_color=THEME["bg_elevated"],
            button_hover_color=THEME["border"],
            dropdown_fg_color=THEME["bg_card"],
            text_color=THEME["text_primary"],
        )
        self.quality_menu.set("1080p")
        self.quality_menu.grid(row=3, column=1, sticky="ew", padx=(6, 0), pady=(0, 12))

        ctk.CTkLabel(
            self.right_frame,
            text="Guardar en",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_secondary"],
        ).grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 4))

        dir_frame = ctk.CTkFrame(self.right_frame, fg_color=THEME["bg_input"], corner_radius=6)
        dir_frame.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 14))
        dir_frame.grid_columnconfigure(0, weight=1)

        self.dir_label = ctk.CTkLabel(
            dir_frame,
            text=self.output_dir,
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        self.dir_label.grid(row=0, column=0, sticky="ew", padx=10, pady=6)

        ctk.CTkButton(
            dir_frame,
            text="Cambiar...",
            width=80,
            height=26,
            fg_color=THEME["bg_elevated"],
            hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._choose_dir,
        ).grid(row=0, column=1, padx=6, pady=4)

        self.download_btn = ctk.CTkButton(
            self.right_frame,
            text="Descargar / Añadir a la cola",
            height=40,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=14, weight="bold"),
            state="disabled",
            command=self._trigger_enqueue,
        )
        self.download_btn.grid(row=6, column=0, columnspan=2, sticky="ew")

    def _on_mode_change(self, value: str) -> None:
        if value == "Solo Audio":
            self.format_menu.configure(values=[f.upper() for f in AUDIO_FORMATS])
            self.format_menu.set("MP3")
            self.quality_header.configure(text="Calidad de audio")
            self.quality_menu.configure(values=AUDIO_QUALITIES)
            self.quality_menu.set(AUDIO_QUALITIES[0])
        else:
            self.format_menu.configure(values=[f.upper() for f in VIDEO_FORMATS])
            self.format_menu.set("MP4")
            self.quality_header.configure(text="Resolución")
            res_list = self.current_media.resolutions if self.current_media else DEFAULT_RESOLUTIONS
            self.quality_menu.configure(values=res_list)
            default_res = "1080p" if "1080p" in res_list else res_list[0]
            self.quality_menu.set(default_res)

    def _choose_dir(self) -> None:
        chosen = filedialog.askdirectory(initialdir=self.output_dir, title="Seleccionar carpeta de descarga")
        if chosen:
            self.output_dir = chosen
            self.dir_label.configure(text=chosen)

    def set_loading(self, is_loading: bool) -> None:
        if is_loading:
            self.title_label.configure(text="Analizando enlace...")
            self.meta_label.configure(text="Obteniendo formatos y resoluciones disponibles...")
            self.download_btn.configure(state="disabled")
            self.playlist_btn.pack_forget()

    def update_media(self, media: MediaInfo) -> None:
        self.current_media = media
        self.selected_indices = set(range(len(media.entries)))

        self.title_label.configure(text=media.title)
        self.meta_label.configure(text=f"{media.channel} • {media.duration}")
        self.download_btn.configure(state="normal")

        if media.is_playlist:
            self._update_playlist_btn_text()
            self.playlist_btn.pack(anchor="w", pady=(8, 0))
        else:
            self.playlist_btn.pack_forget()

        if self.mode_switch.get() == "Video":
            self.quality_menu.configure(values=media.resolutions)
            default_res = "1080p" if "1080p" in media.resolutions else media.resolutions[0]
            self.quality_menu.set(default_res)

        if media.thumbnail_url:
            threading.Thread(target=self._load_thumbnail, args=(media.thumbnail_url,), daemon=True).start()
        else:
            self.thumb_label.configure(image=None, text="Sin miniatura")

    def _update_playlist_btn_text(self) -> None:
        if not self.current_media:
            return
        total = len(self.current_media.entries)
        count = len(self.selected_indices)
        self.playlist_btn.configure(text=f"Seleccionar videos ({count}/{total})")
        self.download_btn.configure(
            text=f"Descargar ({count} videos)" if self.current_media.is_playlist else "Descargar / Añadir a la cola",
            state="normal" if count > 0 else "disabled",
        )

    def _open_playlist_selector(self) -> None:
        if not self.current_media:
            return

        def on_save(new_indices: set[int]) -> None:
            self.selected_indices = new_indices
            self._update_playlist_btn_text()

        PlaylistSelectorDialog(self, self.current_media.entries, self.selected_indices, on_save)

    def _load_thumbnail(self, url: str) -> None:
        try:
            resp = requests.get(url, timeout=8)
            resp.raise_for_status()
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(240, 135))
            self.after(0, lambda: self.thumb_label.configure(image=ctk_img, text=""))
        except Exception:
            self.after(0, lambda: self.thumb_label.configure(image=None, text="Vista previa"))

    def _trigger_enqueue(self) -> None:
        if not self.current_media:
            return
        items = [
            entry
            for idx, entry in enumerate(self.current_media.entries)
            if idx in self.selected_indices
        ]
        if not items:
            return
        mode = "audio" if self.mode_switch.get() == "Solo Audio" else "video"
        container = self.format_menu.get().lower()
        quality = self.quality_menu.get()
        self.on_enqueue(items, mode, container, quality, self.output_dir)
