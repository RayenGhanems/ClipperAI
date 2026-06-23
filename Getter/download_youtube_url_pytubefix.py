#!/usr/bin/env python3
"""Download a YouTube video from a direct URL using pytubefix."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from pytubefix_downloader import (
        choose_merge_streams,
        choose_stream,
        download_and_merge,
        format_stream_label,
        load_pytubefix,
    )
except ImportError as exc:  # pragma: no cover - runtime dependency check
    raise SystemExit(
        "Missing dependency helper. Make sure Getter/pytubefix_downloader.py is present."
    ) from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download a YouTube video from a URL using pytubefix."
    )
    parser.add_argument("url", help="Full YouTube video URL.")
    parser.add_argument(
        "--output-dir",
        default="downloads",
        help="Directory where the file will be saved. Default: downloads",
    )
    parser.add_argument(
        "--filename",
        default=None,
        help="Optional output filename without extension handling.",
    )
    parser.add_argument(
        "--audio-only",
        action="store_true",
        help="Download the audio-only stream instead of video.",
    )
    parser.add_argument(
        "--merge-av",
        action="store_true",
        help="Download separate video/audio streams and merge them into one MP4.",
    )
    parser.add_argument(
        "--keep-parts",
        action="store_true",
        help="When used with --merge-av, keep the separate video/audio files after merging.",
    )
    parser.add_argument(
        "--itag",
        type=int,
        default=None,
        help="Download a specific stream itag, for example 18.",
    )
    parser.add_argument(
        "--oauth",
        action="store_true",
        help="Use pytubefix OAuth flow and cache the login for future downloads.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if args.merge_av and (args.audio_only or args.itag is not None):
            raise ValueError("--merge-av cannot be combined with --audio-only or --itag.")

        YouTube, on_progress = load_pytubefix()
        video_path = None
        audio_path = None
        yt = YouTube(
            args.url,
            use_oauth=args.oauth,
            allow_oauth_cache=args.oauth,
            on_progress_callback=on_progress,
        )
        print(f"Title: {yt.title}")
        print(f"Author: {yt.author}")

        if args.merge_av:
            video_stream, audio_stream = choose_merge_streams(yt)
            print(f"Selected video-only stream: {format_stream_label(video_stream)}")
            print(f"Selected audio-only stream: {format_stream_label(audio_stream)}")
            saved_path, video_path, audio_path = download_and_merge(
                yt,
                output_dir=output_dir,
                filename=args.filename,
                keep_parts=args.keep_parts,
            )
        else:
            stream = choose_stream(yt, audio_only=args.audio_only, itag=args.itag)
            print(f"Selected stream: {format_stream_label(stream)}")
            saved_path = stream.download(
                output_path=str(output_dir),
                filename=args.filename,
            )
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved to: {saved_path}")
    if args.merge_av and args.keep_parts and video_path is not None and audio_path is not None:
        print(f"Video part: {video_path}")
        print(f"Audio part: {audio_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
