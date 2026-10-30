import shutil
from pathlib import Path

THEME = {
    "bg_main": "#0F0F0F",
    "bg_card": "#1E1E1E",
    "bg_elevated": "#262626",
    "bg_input": "#141414",
    "border": "#2D2D2D",
    "accent": "#E11D48",
    "accent_hover": "#BE123C",
    "success": "#10B981",
    "success_hover": "#059669",
    "danger": "#EF4444",
    "danger_hover": "#DC2626",
    "text_primary": "#F8FAFC",
    "text_secondary": "#94A3B8",
    "text_muted": "#64748B",
}

VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "wav"]
AUDIO_QUALITIES = ["320 kbps", "192 kbps", "128 kbps"]
DEFAULT_RESOLUTIONS = ["2160p (4K)", "1440p", "1080p", "720p", "480p", "360p"]

DEFAULT_DOWNLOAD_DIR = str(Path.home() / "Downloads")


def get_ffmpeg_path() -> str | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
