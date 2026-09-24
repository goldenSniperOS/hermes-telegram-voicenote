"""Voice note pipeline: decide, write the script, synthesize, deliver.

The hook never blocks the reply. It captures the routing context, returns
``None`` immediately, and hands the work to a daemon thread. Because the work
runs outside the hook callback, ``plugins.hook_callback_timeout`` cannot kill it.
"""

from __future__ import annotations

import contextvars
import logging
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .delivery import Target
from .guard import DedupGuard
from .script import ScriptWriter, make_script
from .settings import Settings

logger = logging.getLogger(__name__)


@dataclass
class Ports:
    """Host capabilities, injected so the pipeline is testable without Hermes."""

    resolve_target: Callable[[], Target | None]
    is_background_review: Callable[[], bool]
    gateway_is_live: Callable[[], bool]
    synthesize: Callable[..., str]
    send_voice: Callable[[Target, str], None]
    send_text: Callable[[Target, str], None]
    script_writer: ScriptWriter | None = None


class VoiceNotePipeline:
    def __init__(
        self,
        settings: Callable[[], Settings],
        ports: Ports,
        *,
        is_muted: Callable[[Target], bool] = lambda _t: False,
        guard: DedupGuard | None = None,
        start_thread: Callable[[Callable[[], None]], None] | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._settings = settings
        self._ports = ports
        self._is_muted = is_muted
        self._guard = guard or DedupGuard()
        self._start_thread = start_thread or _daemon
        self._sleep = sleep

    # -- hook entry point ----------------------------------------------------

    def on_llm_output(self, response_text: str = "", platform: str = "", **_: Any) -> None:
        """``transform_llm_output`` callback. Always returns None."""
        try:
            job = self._plan(response_text, platform)
            if job is not None:
                context = contextvars.copy_context()
                self._start_thread(lambda: context.run(self._run, *job))
        except Exception:
            logger.exception("telegram-voicenote: failed to schedule voice note")
        return None

    def _plan(self, text: str, platform: str) -> tuple[Target, str, Settings] | None:
        settings = self._settings()
        if not settings.enabled or not text or len(text.strip()) < settings.min_response_chars:
            return None
        if "[[audio_as_voice]]" in text:
            return None  # the agent already attached a voice note
        if self._ports.is_background_review():
            return None  # automatic skill/memory review, not a reply to the user
        if not self._ports.gateway_is_live():
            # A CLI run or a subprocess that inherited HERMES_SESSION_* from a
            # chat turn. Nobody is reading a chat here.
            return None
        target = self._ports.resolve_target()
        if target is None or target.platform not in settings.platforms:
            return None
        if target.chat_type not in settings.chat_types:
            return None
        if platform and platform.lower() != target.platform:
            return None
        if self._is_muted(target):
            return None
        if not self._guard.claim(target.key, text):
            logger.info("telegram-voicenote: duplicate reply for %s skipped", target.key)
            return None
        return target, text, settings

    # -- background work -----------------------------------------------------

    def _run(self, target: Target, text: str, settings: Settings) -> None:
        started = time.monotonic()
        # Let the text reply reach the chat first; the voice note always follows it.
        self._sleep(settings.start_delay)
        writer = self._ports.script_writer if settings.script_mode == "llm" else None
        script = make_script(
            text,
            writer,
            language=settings.language,
            max_words=settings.max_script_words,
            timeout=settings.script_timeout,
            style=settings.style,
        )
        last_error: Exception | None = None
        parts: list[str] = []
        sent = 0
        for attempt in range(settings.retries + 1):
            try:
                if not parts:
                    audio = self._ports.synthesize(
                        script,
                        provider=settings.tts_provider,
                        speed=settings.tts_speed,
                        instructions=settings.tts_instructions,
                    )
                    parts = [audio] if isinstance(audio, str) else list(audio)
                # Long scripts come back as several parts. Send each one once; a
                # retry resumes after the last part that reached the chat.
                while sent < len(parts):
                    self._ports.send_voice(target, parts[sent])
                    sent += 1
                logger.info(
                    "telegram-voicenote: delivered to %s in %.1fs (attempt %d, %d part%s)",
                    target.key,
                    time.monotonic() - started,
                    attempt + 1,
                    len(parts),
                    "" if len(parts) == 1 else "s",
                )
                return
            except Exception as exc:
                last_error = exc
                logger.warning("telegram-voicenote: attempt %d failed: %s", attempt + 1, exc)
                if attempt < settings.retries:
                    self._sleep(2.0 * (attempt + 1))
        logger.error("telegram-voicenote: giving up for %s: %s", target.key, last_error)
        if settings.notify_on_failure:
            try:
                reason = type(last_error).__name__ if last_error else "unknown error"
                self._ports.send_text(target, _format_notice(settings.failure_message, reason))
            except Exception:
                logger.exception("telegram-voicenote: failure notice could not be sent")


def _format_notice(template: str, reason: str) -> str:
    try:
        return template.format(reason=reason)
    except (KeyError, IndexError, ValueError):
        return template


def _daemon(fn: Callable[[], None]) -> None:
    threading.Thread(target=fn, name="telegram-voicenote", daemon=True).start()
