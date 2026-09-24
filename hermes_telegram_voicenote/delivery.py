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
    chat_type: str = "dm"

    @property
    def key(self) -> str:
        # chat_type is descriptive only; it must not change the identity of a chat.
        return f"{self.platform}:{self.chat_id}:{self.thread_id}"


class DeliveryError(RuntimeError):
    pass


def synthesize(
    script: str,
    *,
    provider: str = "",
    speed: float | None = None,
    instructions: str = "",
) -> list[str]:
    """Render *script* with Hermes TTS. Empty options inherit the global tts.* config.

    Returns every audio part in order. Hermes splits long text into chunks and
    reports them in ``file_paths``; ``file_path`` is only the first one.
    """
    from tools.tts_tool import text_to_speech_tool

    kwargs: dict = {}
    if provider:
        kwargs["provider"] = provider
    if speed is not None:
        kwargs["speed"] = speed
    if instructions:
        kwargs["instructions"] = instructions
    result = json.loads(text_to_speech_tool(script, **kwargs))
    if not result.get("success"):
        raise DeliveryError(f"TTS failed: {result.get('error') or result}")
    return audio_paths(result)


def audio_paths(result: dict) -> list[str]:
    paths = [p for p in (result.get("file_paths") or []) if p]
    if not paths and result.get("file_path"):
        paths = [result["file_path"]]
    missing = [p for p in paths if not os.path.exists(p)]
    if not paths or missing:
        raise DeliveryError(f"TTS returned no audio file: {missing or result}")
    for path in paths:
        if os.path.splitext(path)[1].lower() not in VOICE_EXTENSIONS:
            logger.warning(
                "telegram-voicenote: TTS produced %s, not Opus; Telegram may show a file", path
            )
    if len(paths) > 1:
        logger.info("telegram-voicenote: TTS returned %d parts; sending all", len(paths))
    return paths


def live_gateway():
    """The GatewayRunner running in *this* process, or None.

    HERMES_SESSION_* variables are mirrored into os.environ and inherited by
    child processes (terminal tools, scripts). A process that inherited them is
    not a chat. A voice note is only legitimate when this process runs the
    gateway, so this is the decisive check.
    """
    try:
        import gateway.run as gateway_run
    except Exception:
        return None  # not a gateway install (plain CLI): nothing to warn about
    ref = getattr(gateway_run, "_gateway_runner_ref", None)
    if ref is None:
        _warn_once(
            "telegram-voicenote: gateway.run._gateway_runner_ref is missing in this Hermes "
            "version; voice notes are disabled. Please report it."
        )
        return None
    try:
        runner = ref()
    except Exception:
        return None
    if runner is None:
        return None
    if not hasattr(runner, "_gateway_loop"):
        _warn_once(
            "telegram-voicenote: GatewayRunner._gateway_loop is missing in this Hermes "
            "version; voice notes are disabled. Please report it."
        )
        return None
    loop = runner._gateway_loop
    if loop is None or loop.is_closed():
        return None
    return runner


_warned: set[str] = set()


def _warn_once(message: str) -> None:
    if message not in _warned:
        _warned.add(message)
        logger.error(message)


def _platform_config(platform_name: str):
    from gateway.config import Platform

    platform = Platform(platform_name)
    # Use the config the running gateway already loaded. load_gateway_config()
    # re-enters plugin discovery on every call, which is wasted work per voice
    # note and couples delivery to the host's plugin loader.
    runner = live_gateway()
    config = getattr(runner, "config", None) if runner is not None else None
    if config is None:
        from gateway.config import load_gateway_config

        config = load_gateway_config()
    pconfig = config.platforms.get(platform)
    if not pconfig or not pconfig.enabled:
        raise DeliveryError(f"Platform {platform_name!r} is not configured")
    return platform, pconfig


def send_voice(target: Target, audio_path: str) -> None:
    """Send one audio part as a native voice note. Never as a document."""
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
