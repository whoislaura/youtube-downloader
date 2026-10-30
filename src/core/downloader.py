from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
import re
import threading
from typing import Callable
import uuid
import yt_dlp

from src.config import get_ffmpeg_path
from src.core.analyzer import format_duration, parse_height


class DownloadCancelled(Exception):
    pass


@dataclass
class DownloadTask:
    url: str
    title: str
    mode: str  # "video" | "audio"
    container: str  # "mp4", "mkv", "webm", "mp3", "m4a", "wav"
    quality: str  # "1080p", "320 kbps", etc.
    output_dir: str
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    cancel_event: threading.Event = field(default_factory=threading.Event)


def format_speed(speed: float | None) -> str:
    if not speed or speed <= 0:
        return "-- MB/s"
    if speed >= 1024 * 1024:
        return f"{speed / (1024 * 1024):.1f} MB/s"
    return f"{speed / 1024:.0f} KB/s"


def build_ydl_opts(task: DownloadTask, hook: Callable[[dict], None]) -> dict:
    ffmpeg_path = get_ffmpeg_path()
    outtmpl = str(Path(task.output_dir) / "%(title)s.%(ext)s")

    opts: dict = {
        "outtmpl": outtmpl,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
    }
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path

    if task.mode == "audio":
        match = re.search(r"(\d+)", task.quality)
        bitrate = match.group(1) if match else "192"
        opts["format"] = "bestaudio/best"
        if ffmpeg_path:
            # FFmpegVideoConvertor converts audio using ffmpeg directly without requiring ffprobe
            opts["postprocessors"] = [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": task.container,
                }
            ]
            opts["postprocessor_args"] = {"videoconvertor": ["-vn", "-b:a", f"{bitrate}k"]}
    else:
        height = parse_height(task.quality)
        if ffmpeg_path:
            opts["format"] = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
            opts["merge_output_format"] = task.container
        else:
            opts["format"] = f"best[height<={height}]/best"

    return opts


class DownloadManager:
    # shortcut: max_workers=2 fixed pool, make configurable if power users need high-bandwidth batching
    def __init__(
        self,
        on_progress: Callable[[str, float, str, str, str], None],
        on_complete: Callable[[str, str], None],
        on_error: Callable[[str, str, bool], None],
        max_workers: int = 2,
    ):
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: dict[str, DownloadTask] = {}

    def enqueue(self, task: DownloadTask) -> str:
        self.tasks[task.task_id] = task
        self.executor.submit(self._run, task)
        return task.task_id

    def cancel(self, task_id: str) -> None:
        task = self.tasks.get(task_id)
        if task:
            task.cancel_event.set()

    def shutdown(self) -> None:
        for task in self.tasks.values():
            task.cancel_event.set()
        self.executor.shutdown(wait=False, cancel_futures=True)

    def _run(self, task: DownloadTask) -> None:
        if task.cancel_event.is_set():
            self.on_error(task.task_id, "Cancelado", True)
            return

        Path(task.output_dir).mkdir(parents=True, exist_ok=True)

        def hook(d: dict) -> None:
            if task.cancel_event.is_set():
                raise DownloadCancelled("Cancelado por el usuario")

            status = d.get("status")
            if status == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                downloaded = d.get("downloaded_bytes") or 0
                pct = min(max(downloaded / total, 0.0), 1.0) if total > 0 else 0.0
                speed_str = format_speed(d.get("speed"))
                eta_str = format_duration(d.get("eta")) if d.get("eta") else "--:--"
                self.on_progress(task.task_id, pct, speed_str, eta_str, "Descargando...")
            elif status == "finished":
                self.on_progress(task.task_id, 1.0, "", "", "Procesando archivo...")

        opts = build_ydl_opts(task, hook)
        try:
            self.on_progress(task.task_id, 0.0, "-- MB/s", "--:--", "Iniciando...")
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([task.url])
            self.on_complete(task.task_id, task.output_dir)
        except DownloadCancelled:
            self.on_error(task.task_id, "Cancelado", True)
        except Exception as exc:
            if task.cancel_event.is_set():
                self.on_error(task.task_id, "Cancelado", True)
            else:
                self.on_error(task.task_id, str(exc), False)
