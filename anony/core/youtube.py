# Copyright (c) 2025
# This file is part of AnonXMusic (Modified for VNIOX API)

import os
import re
import random
import asyncio
from pathlib import Path
from typing import Optional, Union

import aiohttp
import yt_dlp
from pyrogram import enums, types

from anony.helpers import Track, utils
from config import VNIOX_API_KEY, VNIOX_BASE


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.regex = r"(https?://)?(www\.|m\.)?(youtube\.com/(watch\?v=|shorts/)|youtu\.be/)([a-zA-Z0-9_-]{11})"

    # -------- Extract Cookies -------- #
    def get_cookies(self):
        if not self.checked:
            if os.path.exists("anony/cookies"):
                for file in os.listdir("anony/cookies"):
                    if file.endswith(".txt"):
                        self.cookies.append(file)
            self.checked = True
        return f"anony/cookies/{random.choice(self.cookies)}" if self.cookies else None

    # -------- Validate YouTube URLs -------- #
    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    # -------- Extract URL From Message -------- #
    def url(self, message_1: types.Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)

        for message in messages:
            text = message.text or message.caption or ""

            if message.entities:
                for entity in message.entities:
                    if entity.type == enums.MessageEntityType.URL:
                        return text[entity.offset : entity.offset + entity.length]

            if message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == enums.MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    # -------- VNIOX API Search -------- #
    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        url = f"{VNIOX_BASE}/api/yt/search?query={query}&key={VNIOX_API_KEY}"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as r:
                data = await r.json()

        items = data.get("result") or data.get("data") or []
        if not items:
            return None

        info = items[0]

        return Track(
            id=info["id"],
            channel_name=info.get("channel"),
            duration=info.get("duration"),
            duration_sec=utils.to_seconds(info.get("duration")),
            message_id=m_id,
            title=info["title"][:25],
            thumbnail=info.get("thumbnail"),
            url=f"https://www.youtube.com/watch?v={info['id']}",
            view_count=info.get("views"),
            video=video,
        )

    # -------- Download Audio / Video -------- #
    async def download(self, video_id: str, video: bool = False) -> Optional[str]:
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "ignoreerrors": True,
            "nocheckcertificate": True,
            "cookiefile": self.get_cookies(),
        }

        if video:
            ydl_opts = {
                **base_opts,
                "format": "(bestvideo[height<=720][ext=mp4])+bestaudio",
                "merge_output_format": "mp4",
            }
        else:
            ydl_opts = {
                **base_opts,
                "format": "bestaudio/best",
            }

        def _download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return filename

        return await asyncio.to_thread(_download)
