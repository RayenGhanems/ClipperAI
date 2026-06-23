#!/usr/bin/env python3
"""Find a channel's latest upload with the YouTube API and download it with pytubefix."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import urlopen

from pytubefix_downloader import (
    choose_merge_streams,
    choose_stream,
    download_and_merge,
    format_stream_label,
    load_pytubefix,
)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
API_KEY_ENV_VARS = ("YOUTUBE_API_KEY", "Youtube_API_KEY")


def load_env_files() -> None:
    candidates = [Path(".env"), Path(".env ")]
    candidates.extend(sorted(Path.cwd().glob(".env*")))

    seen: set[Path] = set()
    for env_path in candidates:
        env_path = env_path.resolve()
        if env_path in seen or not env_path.is_file():
            continue
        seen.add(env_path)
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def resolve_api_key(explicit_api_key: str | None) -> str:
    if explicit_api_key:
        return explicit_api_key

    for env_name in API_KEY_ENV_VARS:
        value = os.environ.get(env_name)
        if value:
            return value

    raise RuntimeError(
        "Missing YouTube API key. Set YOUTUBE_API_KEY or Youtube_API_KEY in your environment or a .env file."
    )


def youtube_api_get(endpoint: str, **params: str) -> dict[str, Any]:
    query = urlencode(params)
    url = f"{YOUTUBE_API_BASE}/{endpoint}?{query}"

    try:
        with urlopen(url) as response:
            return json.load(response)
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(details)
            message = payload["error"]["message"]
        except Exception:
            message = details or str(exc)
        raise RuntimeError(f"YouTube API request failed: {message}") from exc
    except URLError as exc:
        raise RuntimeError(f"Network error while calling YouTube API: {exc.reason}") from exc


def classify_channel_input(channel: str) -> tuple[str, str]:
    """Accept a handle, channel id, username, custom URL, or a full channel URL."""
    channel = channel.strip()
    parsed = urlparse(channel)

    if parsed.scheme and parsed.netloc:
        host = parsed.netloc.lower()
        path = parsed.path.strip("/")
        parts = [part for part in path.split("/") if part]

        if "youtube.com" in host or host == "youtu.be":
            if host == "youtu.be":
                raise ValueError("Expected a channel, but received a video URL.")
            if "v" in parse_qs(parsed.query):
                raise ValueError("Expected a channel, but received a video URL.")
            if parts:
                if parts[0] in {"watch", "shorts", "live"}:
                    raise ValueError("Expected a channel, but received a video URL.")
                if parts[0].startswith("@"):
                    return "handle", parts[0]
                if parts[0] == "channel" and len(parts) > 1:
                    return "id", parts[1]
                if parts[0] == "user" and len(parts) > 1:
                    return "username", parts[1]
                if parts[0] == "c" and len(parts) > 1:
                    return "search", parts[1]

    if channel.startswith("@"):
        return "handle", channel
    if CHANNEL_ID_RE.fullmatch(channel):
        return "id", channel

    return "search", channel


def get_channel_by(param_name: str, param_value: str, api_key: str) -> dict[str, str]:
    response = youtube_api_get(
        "channels",
        part="snippet,contentDetails",
        key=api_key,
        **{param_name: param_value},
    )
    items = response.get("items", [])
    if not items:
        raise LookupError(f"Channel lookup failed for {param_name}={param_value}.")

    item = items[0]
    return {
        "channel_id": item["id"],
        "channel_title": item["snippet"]["title"],
        "uploads_playlist": item["contentDetails"]["relatedPlaylists"]["uploads"],
    }


def find_channel(channel_input: str, api_key: str) -> dict[str, str]:
    kind, value = classify_channel_input(channel_input)

    if kind == "id":
        return get_channel_by("id", value, api_key)
    if kind == "handle":
        return get_channel_by("forHandle", value.lstrip("@"), api_key)
    if kind == "username":
        return get_channel_by("forUsername", value, api_key)

    for resolver, resolver_value in (
        ("forHandle", value.lstrip("@")),
        ("forUsername", value),
    ):
        try:
            return get_channel_by(resolver, resolver_value, api_key)
        except LookupError:
            pass

    search_response = youtube_api_get(
        "search",
        part="snippet",
        type="channel",
        q=value,
        maxResults="1",
        key=api_key,
    )
    items = search_response.get("items", [])
    if not items:
        raise LookupError(f"No YouTube channel matched '{channel_input}'.")

    return get_channel_by("id", items[0]["id"]["channelId"], api_key)


def get_latest_video(uploads_playlist: str, api_key: str) -> dict[str, str]:
    response = youtube_api_get(
        "playlistItems",
        part="snippet,contentDetails",
        playlistId=uploads_playlist,
        maxResults="5",
        key=api_key,
    )
    items = response.get("items", [])
    if not items:
        raise LookupError("The channel has no uploaded videos.")

    def published_at(item: dict[str, Any]) -> str:
        return (
            item.get("contentDetails", {}).get("videoPublishedAt")
            or item.get("snippet", {}).get("publishedAt")
            or ""
        )

    latest = max(items, key=published_at)
    return {
        "video_id": latest["contentDetails"]["videoId"],
        "title": latest["snippet"]["title"],
        "published_at": published_at(latest),
    }


def build_video_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"


def download_video(video_url: str, output_dir: Path, args: argparse.Namespace) -> Path:
    YouTube, on_progress = load_pytubefix()
    output_dir.mkdir(parents=True, exist_ok=True)

    yt = YouTube(
        video_url,
        use_oauth=args.oauth,
        allow_oauth_cache=args.oauth,
        on_progress_callback=on_progress,
    )

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
        if args.keep_parts:
            print(f"Video part: {video_path}")
            print(f"Audio part: {audio_path}")
        return saved_path

    stream = choose_stream(yt, audio_only=args.audio_only, itag=args.itag)
    print(f"Selected stream: {format_stream_label(stream)}")
    saved_path = stream.download(
        output_path=str(output_dir),
        filename=args.filename,
    )
    return Path(saved_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resolve a YouTube channel, find its latest upload, and download it."
    )
    parser.add_argument(
        "channel",
        help="Channel handle, channel ID, username, custom URL, or full YouTube channel URL.",
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="YouTube Data API key. Defaults to YOUTUBE_API_KEY or Youtube_API_KEY.",
    )
    parser.add_argument(
        "--output-dir",
        default="downloads",
        help="Directory where the file will be saved. Default: downloads",
    )
    parser.add_argument(
        "--filename",
        default=None,
        help="Optional output filename for the downloaded file.",
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
    parser.add_argument(
        "--print-only",
        action="store_true",
        help="Only print the latest video URL without downloading it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    load_env_files()

    if args.merge_av and (args.audio_only or args.itag is not None):
        print("--merge-av cannot be combined with --audio-only or --itag.", file=sys.stderr)
        return 1

    try:
        api_key = resolve_api_key(args.api_key)
        channel = find_channel(args.channel, api_key)
        latest_video = get_latest_video(channel["uploads_playlist"], api_key)
    except (LookupError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    video_url = build_video_url(latest_video["video_id"])
    print(f"Channel: {channel['channel_title']}")
    print(f"Latest video: {latest_video['title']}")
    print(f"Published: {latest_video['published_at']}")
    print(f"URL: {video_url}")

    if args.print_only:
        return 0

    try:
        saved_path = download_video(video_url, Path(args.output_dir), args)
    except Exception as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1

    print(f"Saved to: {saved_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
