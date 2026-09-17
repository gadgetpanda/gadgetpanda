"""Resolve an ffmpeg binary for RTSP preview.

pip cannot install OS packages, but ``imageio-ffmpeg`` ships a static binary
inside the wheel — so ``pip install 'gadgetpanda[ui]'`` is enough for preview.
"""

from __future__ import annotations

import shutil
from functools import lru_cache


@lru_cache(maxsize=1)
def resolve_ffmpeg() -> str | None:
    """Return path to ffmpeg: system PATH first, then imageio-ffmpeg wheel."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None
