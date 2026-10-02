"""YouTube feed and optional transcript helpers."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from saathi.adapters.rss import RssSource
from saathi.domain.ports import Clock, HttpClient


def youtube_source(name: str, channel_id: str, http: HttpClient, clock: Clock) -> RssSource:
    """Build a public YouTube channel feed source."""

    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    return RssSource(name, url, http, clock, max_age_hours=72, limit=5)


def transcript_excerpt(url: str, chars: int = 1200) -> str | None:
    """Return an auto-caption excerpt when the optional yt-dlp extra exists."""

    executable = shutil.which("yt-dlp")
    if executable is None:
        return None
    with tempfile.TemporaryDirectory(prefix="saathi-subs-") as directory:
        target = Path(directory) / "captions"
        try:
            subprocess.run(
                [
                    executable,
                    "--skip-download",
                    "--write-auto-subs",
                    "--write-subs",
                    "--sub-langs",
                    "en.*,hi.*",
                    "--sub-format",
                    "vtt",
                    "-o",
                    str(target),
                    url,
                ],
                capture_output=True,
                check=False,
                timeout=90,
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        files = sorted(Path(directory).glob("*.vtt"))
        return _read_vtt(files[0], chars) if files else None


def _read_vtt(path: Path, chars: int) -> str:
    lines: list[str] = []
    previous = ""
    for raw in path.read_text(errors="replace").splitlines():
        line = raw.strip()
        if not line or "-->" in line or line.startswith(("WEBVTT", "Kind:", "Language:")):
            continue
        if line != previous:
            lines.append(line)
            previous = line
    return " ".join(lines)[:chars]
