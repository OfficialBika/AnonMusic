# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic

import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils


class DummyLogger:
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.warned = False
        self.cookie_dir = "anony/cookies"
        self._download_locks: dict[tuple[str, bool], asyncio.Lock] = {}
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def get_cookies(self):
        if not self.checked:
            try:
                self.cookies = [
                    f"{self.cookie_dir}/{file}"
                    for file in os.listdir(self.cookie_dir) if file.endswith(".txt")
                ]
            except FileNotFoundError:
                self.cookies = []
            self.checked = True
        if not self.cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        return random.choice(self.cookies)

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        os.makedirs(self.cookie_dir, exist_ok=True)
        timeout = aiohttp.ClientTimeout(total=20, connect=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            for url in urls:
                name = url.rstrip("/").split("/")[-1]
                if not name or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", name):
                    logger.warning("Skipping invalid cookie identifier")
                    continue
                async with session.get("https://batbin.me/raw/" + name) as resp:
                    resp.raise_for_status()
                    payload = await resp.read()
                    if not payload or len(payload) > 2_000_000:
                        raise ValueError(f"Cookie payload size invalid for {name}")
                    (Path(self.cookie_dir) / f"{name}.txt").write_bytes(payload)
        self.checked = False
        self.cookies.clear()
        logger.info("Cookies saved in %s.", self.cookie_dir)

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            results = await VideosSearch(query, limit=1, with_live=False).next()
        except Exception:
            logger.warning("YouTube search failed", exc_info=True)
            return None
        if results and results.get("result"):
            data = results["result"][0]
            thumbs = data.get("thumbnails") or [{}]
            duration = data.get("duration")
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=duration,
                duration_sec=utils.to_seconds(duration) if duration else 0,
                message_id=m_id,
                title=(data.get("title") or "Unknown title")[:25],
                thumbnail=(thumbs[-1].get("url") or "").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track]:
        tracks = []
        try:
            playlist = await Playlist.get(url)
            for data in playlist.get("videos", [])[:limit]:
                thumbs = data.get("thumbnails") or [{}]
                video_id, link, duration = data.get("id"), data.get("link"), data.get("duration")
                if not video_id or not link or not duration:
                    continue
                tracks.append(Track(
                    id=video_id,
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=duration,
                    duration_sec=utils.to_seconds(duration),
                    title=(data.get("title") or "Unknown title")[:25],
                    thumbnail=(thumbs[-1].get("url") or "").split("?")[0],
                    url=link.split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                ))
        except Exception:
            logger.warning("YouTube playlist fetch failed", exc_info=True)
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(video_id)):
            logger.warning("Refusing download with invalid YouTube id")
            return None
        key = (str(video_id), video)
        lock = self._download_locks.setdefault(key, asyncio.Lock())
        async with lock:
            filename = Path("downloads") / f"{video_id}.{'mp4' if video else 'webm'}"
            try:
                if filename.is_file() and filename.stat().st_size > 0:
                    return str(filename)
            except OSError:
                pass
            filename.parent.mkdir(parents=True, exist_ok=True)
            base_opts = {
                "outtmpl": "downloads/%(id)s.%(ext)s",
                "quiet": True, "noplaylist": True, "geo_bypass": True,
                "no_warnings": True, "overwrites": False, "logger": DummyLogger(),
                "nocheckcertificate": False,
                "cookiefile": self.get_cookies(),
                "remote_components": ["ejs:github"],
            }
            if video:
                ydl_opts = {
                    **base_opts,
                    "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio)",
                    "merge_output_format": "mp4",
                }
            else:
                ydl_opts = {**base_opts, "format": "bestaudio[ext=webm][acodec=opus]"}

            def _download():
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        result = ydl.download([self.base + video_id])
                    if result or not filename.is_file() or filename.stat().st_size <= 0:
                        return None
                    return str(filename)
                except (yt_dlp.utils.DownloadError, yt_dlp.utils.ExtractorError):
                    return None
                except Exception:
                    logger.warning("Download failed for %s", video_id, exc_info=True)
                    return None

            return await asyncio.to_thread(_download)
