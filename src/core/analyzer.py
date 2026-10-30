from dataclasses import dataclass, field
import re
import yt_dlp
from src.config import DEFAULT_RESOLUTIONS


@dataclass
class VideoItem:
    url: str
    title: str
    duration: str
    channel: str = ""
    thumbnail_url: str = ""


@dataclass
class MediaInfo:
    url: str
    title: str
    channel: str
    duration: str
    thumbnail_url: str
    is_playlist: bool = False
    resolutions: list[str] = field(default_factory=lambda: list(DEFAULT_RESOLUTIONS))
    entries: list[VideoItem] = field(default_factory=list)


def format_duration(seconds: int | float | None) -> str:
    if not seconds:
        return "--:--"
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def label_for_height(height: int) -> str:
    if height >= 2160:
        return f"{height}p (4K)"
    if height == 1440:
        return "1440p (2K)"
    return f"{height}p"


def parse_height(res_label: str) -> int:
    match = re.search(r"(\d+)", res_label)
    return int(match.group(1)) if match else 1080


def analyze_url(url: str) -> MediaInfo:
    clean_url = url.strip()
    if not clean_url.startswith(("http://", "https://")):
        raise ValueError("Ingresa un enlace válido (http:// o https://).")

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": "in_playlist",
        "skip_download": True,
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(clean_url, download=False)

    if not info:
        raise ValueError("No se pudo obtener información del enlace.")

    if info.get("_type") == "playlist" or "entries" in info:
        raw_entries = [e for e in (info.get("entries") or []) if e]
        if not raw_entries:
            raise ValueError("La lista de reproducción está vacía o es privada.")

        items: list[VideoItem] = []
        first_thumb = info.get("thumbnail") or ""
        for entry in raw_entries:
            vid_url = entry.get("url") or entry.get("webpage_url") or ""
            if vid_url and not vid_url.startswith("http"):
                vid_url = f"https://www.youtube.com/watch?v={vid_url}"
            thumbs = entry.get("thumbnails") or []
            thumb = entry.get("thumbnail") or (thumbs[-1].get("url") if thumbs else "")
            if not first_thumb and thumb:
                first_thumb = thumb
            items.append(
                VideoItem(
                    url=vid_url,
                    title=entry.get("title") or "Video sin título",
                    duration=format_duration(entry.get("duration")),
                    channel=entry.get("uploader") or entry.get("channel") or "",
                    thumbnail_url=thumb,
                )
            )

        return MediaInfo(
            url=clean_url,
            title=info.get("title") or "Lista de reproducción",
            channel=info.get("uploader") or info.get("channel") or "YouTube Playlist",
            duration=f"{len(items)} videos",
            thumbnail_url=first_thumb,
            is_playlist=True,
            resolutions=list(DEFAULT_RESOLUTIONS),
            entries=items,
        )

    heights = sorted(
        {
            int(f["height"])
            for f in (info.get("formats") or [])
            if f.get("vcodec") not in (None, "none") and f.get("height") and int(f["height"]) >= 144
        },
        reverse=True,
    )
    resolutions = [label_for_height(h) for h in heights] if heights else list(DEFAULT_RESOLUTIONS)

    video_url = info.get("webpage_url") or clean_url
    title = info.get("title") or "Video de YouTube"
    channel = info.get("uploader") or info.get("channel") or "Desconocido"
    duration = format_duration(info.get("duration"))
    thumb = info.get("thumbnail") or ""

    return MediaInfo(
        url=video_url,
        title=title,
        channel=channel,
        duration=duration,
        thumbnail_url=thumb,
        is_playlist=False,
        resolutions=resolutions,
        entries=[VideoItem(url=video_url, title=title, duration=duration, channel=channel, thumbnail_url=thumb)],
    )
