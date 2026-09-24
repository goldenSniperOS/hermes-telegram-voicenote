"""Host adapters: speech synthesis and Telegram voice delivery via Hermes internals.

This is the only module coupled to Hermes internal APIs. Keep it thin so a
Hermes upgrade that moves these functions only needs changes here.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass

logger = logging.getLogger(__name__)

VOICE_EXTENSIONS = {".ogg", ".opus"}


@dataclass(frozen=True)
class Target:
    platform: str
    chat_id: str
    thread_id: str = ""

    @property
    def key(self) -> str:
        return f"{self.platform}:{self.chat_id}:{self.thread_id}"


class DeliveryError(RuntimeError):
    pass


def synthesize(script: str) -> str:
    """Render *script* with the TTS provider and voice configured in Hermes."""
    from tools.tts_tool import text_to_speech_tool

    result = json.loads(text_to_speech_tool(script))
    if not result.get("success"):
        raise DeliveryError(f"TTS failed: {result.get('error') or result}")
    path = result.get("file_path") or ""
    if not path or not os.path.exists(path):
        raise DeliveryError(f"TTS returned no audio file: {result}")
    if os.path.splitext(path)[1].lower() not in VOICE_EXTENSIONS:
        logger.warning(
            "telegram-voicenote: TTS produced %s, not Opus; Telegram may show a file", path
        )
    return path


def _platform_config(platform_name: str):
    from gateway.config import Platform, load_gateway_config

    platform = Platform(platform_name)
    pconfig = load_gateway_config().platforms.get(platform)
    if not pconfig or not pconfig.enabled:
        raise DeliveryError(f"Platform {platform_name!r} is not configured")
    return platform, pconfig


def send_voice(target: Target, audio_path: str) -> None:
    """Send *audio_path* as a native voice note. Never as a document."""
    from tools.send_message_tool import _send_to_platform

    platform, pconfig = _platform_config(target.platform)
    result = asyncio.run(
        _send_to_platform(
            platform,
            pconfig,
            target.chat_id,
            "",
            thread_id=target.thread_id or None,
            media_files=[(audio_path, True)],
        )
    )
    if not isinstance(result, dict) or not result.get("success"):
        raise DeliveryError(f"Send failed: {result}")


def send_text(target: Target, message: str) -> None:
    from tools.send_message_tool import _send_to_platform

    platform, pconfig = _platform_config(target.platform)
    asyncio.run(
        _send_to_platform(
            platform, pconfig, target.chat_id, message, thread_id=target.thread_id or None
        )
    )
