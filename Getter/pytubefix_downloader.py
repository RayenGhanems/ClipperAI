#!/usr/bin/env python3
"""Helpers for downloading YouTube media with pytubefix."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Any


def load_pytubefix() -> tuple[Any, Any]:
    try:
        from pytubefix import YouTube
        from pytubefix.cli import on_progress
    except ImportError as exc:
        raise RuntimeError(
            "pytubefix is not installed in this Python environment. "
            "Install it with 'python -m pip install pytubefix'."
        ) from exc
    return YouTube, on_progress


def format_stream_label(stream: Any) -> str:
    return (
        f"itag={stream.itag}, mime_type={stream.mime_type}, "
        f"res={stream.resolution}, abr={stream.abr}"
    )


def choose_stream(yt: Any, audio_only: bool = False, itag: int | None = None) -> Any:
    if itag is not None:
        stream = yt.streams.get_by_itag(itag)
        if stream is None:
            raise ValueError(f"No stream found for itag {itag}.")
        return stream

    if audio_only:
        stream = yt.streams.get_audio_only()
        if stream is None:
            raise ValueError("No audio-only stream was found.")
        return stream

    # Prefer a progressive MP4 so the result is a single playable file.
    stream = (
        yt.streams.filter(progressive=True, file_extension="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )
    if stream is not None:
        return stream

    stream = yt.streams.get_highest_resolution()
    if stream is None:
        raise ValueError("No downloadable video stream was found.")
    return stream


def choose_merge_streams(yt: Any) -> tuple[Any, Any]:
    video_stream = (
        yt.streams.filter(only_video=True, subtype="mp4")
        .order_by("resolution")
        .desc()
        .first()
    )
    if video_stream is None:
        raise ValueError("No MP4 video-only stream was found for merging.")

    audio_stream = (
        yt.streams.filter(only_audio=True, mime_type="audio/mp4")
        .order_by("abr")
        .desc()
        .first()
    )
    if audio_stream is None:
        audio_stream = yt.streams.get_audio_only()
    if audio_stream is None:
        raise ValueError("No audio-only stream was found for merging.")

    return video_stream, audio_stream


def detect_ffmpeg_command() -> list[str]:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        return [ffmpeg_path]

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "FFmpeg is required to merge video and audio. "
            "Install system ffmpeg or run 'python -m pip install imageio-ffmpeg'."
        ) from exc

    return [imageio_ffmpeg.get_ffmpeg_exe()]


def build_base_name(title: str, filename: str | None) -> str:
    if filename:
        return Path(filename).stem
    return title


def download_stream(stream: Any, output_dir: Path, filename: str) -> Path:
    saved_path = stream.download(
        output_path=str(output_dir),
        filename=filename,
        skip_existing=False,
    )
    return Path(saved_path)


def merge_streams(video_path: Path, audio_path: Path, output_path: Path) -> Path:
    command = detect_ffmpeg_command() + [
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    subprocess.run(command, check=True)
    return output_path


def download_and_merge(
    yt: Any,
    output_dir: Path,
    filename: str | None = None,
    keep_parts: bool = False,
) -> tuple[Path, Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    base_name = build_base_name(yt.title, filename)
    video_stream, audio_stream = choose_merge_streams(yt)

    video_ext = video_stream.subtype or "mp4"
    audio_ext = audio_stream.subtype or "m4a"
    video_path = download_stream(video_stream, output_dir, f"{base_name}.video.{video_ext}")
    audio_path = download_stream(audio_stream, output_dir, f"{base_name}.audio.{audio_ext}")
    merged_path = merge_streams(video_path, audio_path, output_dir / f"{base_name}.mp4")

    if not keep_parts:
        video_path.unlink(missing_ok=True)
        audio_path.unlink(missing_ok=True)

    return merged_path, video_path, audio_path
