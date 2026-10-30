import threading
import customtkinter as ctk

from src.config import THEME, get_ffmpeg_path
from src.core.analyzer import MediaInfo, VideoItem, analyze_url
from src.core.downloader import DownloadManager, DownloadTask
from src.ui.preview_panel import PreviewPanel
from src.ui.queue_panel import QueuePanel


class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")

        self.title("Crimson Studio • YouTube Downloader")
        self.geometry("860x690")
        self.minsize(780, 620)
        self.configure(fg_color=THEME["bg_main"])

        self._closing = False
        self.download_manager = DownloadManager(
            on_progress=lambda tid, pct, spd, eta, stg: self._ui_call(
                self.queue_panel.update_progress, tid, pct, spd, eta, stg
            ),
            on_complete=lambda tid, out: self._ui_call(self.queue_panel.mark_completed, tid, out),
            on_error=lambda tid, msg, canc: self._ui_call(self.queue_panel.mark_error, tid, msg, canc),
        )

        self._build_ui()

    def _ui_call(self, func, *args) -> None:
        if not self._closing:
            try:
                self.after(0, func, *args)
            except Exception:
                pass

    def destroy(self) -> None:
        self._closing = True
        self.download_manager.shutdown()
        super().destroy()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Top header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))

        dot = ctk.CTkLabel(
            header,
            text="●",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["accent"],
        )
        dot.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(
            header,
            text="YouTube Studio Downloader",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME["text_primary"],
        ).pack(side="left")

        ffmpeg_ok = bool(get_ffmpeg_path())
        ctk.CTkLabel(
            header,
            text="FFmpeg activo (1080p/4K + MP3)" if ffmpeg_ok else "Sin FFmpeg (calidad limitada)",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=THEME["bg_card"],
            text_color=THEME["success"] if ffmpeg_ok else THEME["danger"],
            corner_radius=6,
            padx=10,
            pady=4,
        ).pack(side="right")

        # URL input bar
        url_card = ctk.CTkFrame(
            self,
            fg_color=THEME["bg_card"],
            corner_radius=12,
            border_width=1,
            border_color=THEME["border"],
        )
        url_card.grid(row=1, column=0, sticky="ew", padx=20, pady=6)
        url_card.grid_columnconfigure(0, weight=1)

        self.url_entry = ctk.CTkEntry(
            url_card,
            placeholder_text="Pega aquí el enlace de YouTube (video o playlist)...",
            height=40,
            fg_color=THEME["bg_input"],
            border_color=THEME["border"],
            text_color=THEME["text_primary"],
            placeholder_text_color=THEME["text_muted"],
            font=ctk.CTkFont(size=13),
        )
        self.url_entry.grid(row=0, column=0, sticky="ew", padx=(14, 8), pady=(12, 4))
        self.url_entry.bind("<Return>", lambda _e: self._start_analysis())

        ctk.CTkButton(
            url_card,
            text="Pegar",
            width=75,
            height=40,
            fg_color=THEME["bg_elevated"],
            hover_color=THEME["border"],
            text_color=THEME["text_primary"],
            command=self._paste_clipboard,
        ).grid(row=0, column=1, padx=4, pady=(12, 4))

        self.analyze_btn = ctk.CTkButton(
            url_card,
            text="Analizar",
            width=110,
            height=40,
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._start_analysis,
        )
        self.analyze_btn.grid(row=0, column=2, padx=(4, 14), pady=(12, 4))

        self.feedback_lbl = ctk.CTkLabel(
            url_card,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=THEME["text_secondary"],
            anchor="w",
        )
        self.feedback_lbl.grid(row=1, column=0, columnspan=3, sticky="w", padx=16, pady=(0, 8))

        # Preview & Options panel
        self.preview_panel = PreviewPanel(self, on_enqueue=self._enqueue_items)
        self.preview_panel.grid(row=2, column=0, sticky="ew", padx=20, pady=6)

        # Download Queue panel
        self.queue_panel = QueuePanel(self, on_cancel=self.download_manager.cancel)
        self.queue_panel.grid(row=3, column=0, sticky="nsew", padx=20, pady=(6, 18))

    def _paste_clipboard(self) -> None:
        try:
            text = self.clipboard_get().strip()
            if text:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, text)
                self._start_analysis()
        except Exception:
            self._set_feedback("El portapapeles está vacío.", is_error=True)

    def _set_feedback(self, message: str, is_error: bool = False) -> None:
        color = THEME["danger"] if is_error else THEME["text_secondary"]
        self.feedback_lbl.configure(text=message, text_color=color)

    def _start_analysis(self) -> None:
        url = self.url_entry.get().strip()
        if not url:
            self._set_feedback("Por favor, pega un enlace de YouTube primero.", is_error=True)
            return

        self.analyze_btn.configure(state="disabled", text="Analizando...")
        self._set_feedback("Consultando información del enlace...", is_error=False)
        self.preview_panel.set_loading(True)

        threading.Thread(target=self._run_analysis, args=(url,), daemon=True).start()

    def _run_analysis(self, url: str) -> None:
        try:
            info = analyze_url(url)
            self.after(0, self._on_analysis_success, info)
        except Exception as exc:
            self.after(0, self._on_analysis_error, str(exc))

    def _on_analysis_success(self, info: MediaInfo) -> None:
        self.analyze_btn.configure(state="normal", text="Analizar")
        kind = f"Playlist con {len(info.entries)} videos lista." if info.is_playlist else "Video listo para descargar."
        self._set_feedback(kind, is_error=False)
        self.preview_panel.update_media(info)

    def _on_analysis_error(self, error_msg: str) -> None:
        self.analyze_btn.configure(state="normal", text="Analizar")
        self.preview_panel.set_loading(False)
        self._set_feedback(f"No se pudo analizar: {error_msg}", is_error=True)

    def _enqueue_items(
        self,
        items: list[VideoItem],
        mode: str,
        container: str,
        quality: str,
        output_dir: str,
    ) -> None:
        badge = f"{container.upper()} • {quality}"
        for item in items:
            task = DownloadTask(
                url=item.url,
                title=item.title,
                mode=mode,
                container=container,
                quality=quality,
                output_dir=output_dir,
            )
            self.queue_panel.add_item(task.task_id, item.title, badge, output_dir)
            self.download_manager.enqueue(task)
        self._set_feedback(f"Se añadieron {len(items)} descarga(s) a la cola.", is_error=False)
