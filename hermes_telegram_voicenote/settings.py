"""Plugin settings read from ``plugins.entries.telegram-voicenote.settings``.

Every value has a safe default so the plugin works with zero configuration.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Getter = Callable[[str, Any], Any]

SCRIPT_MODES = ("llm", "plain")
CHAT_TYPES = ("dm", "group", "forum")
DEFAULT_FAILURE_MESSAGE = "I could not generate the voice note for this reply ({reason})."


@dataclass(frozen=True)
class Settings:
    # When to send
    enabled: bool = True
    platforms: tuple[str, ...] = ("telegram",)
    chat_types: tuple[str, ...] = CHAT_TYPES
    min_response_chars: int = 1
    start_delay: float = 1.5
    # What to say
    script_mode: str = "llm"
    language: str = "auto"
    max_script_words: int = 180
    style: str = ""
    script_timeout: float = 90.0
    # How it sounds (empty = use the global tts.* settings)
    tts_provider: str = ""
    tts_speed: float | None = None
    tts_instructions: str = ""
    # Reliability
    retries: int = 2
    notify_on_failure: bool = True
    failure_message: str = DEFAULT_FAILURE_MESSAGE

    @classmethod
    def load(cls, get: Getter) -> Settings:
        d = cls()

        def pick(key: str, cast: Callable[[Any], Any]) -> Any:
            fallback = getattr(d, key)
            try:
                value = get(key, fallback)
                if value is None:
                    return fallback
                return cast(value)
            except (TypeError, ValueError):
                return fallback

        def words(key: str, allowed: tuple[str, ...] | None = None) -> tuple[str, ...]:
            raw = pick(key, lambda v: tuple(str(p).strip().lower() for p in v if str(p).strip()))
            if allowed:
                raw = tuple(v for v in raw if v in allowed)
            return raw or getattr(d, key)

        script_mode = str(pick("script_mode", str)).strip().lower()
        speed = pick("tts_speed", float)
        return cls(
            enabled=pick("enabled", _to_bool),
            platforms=words("platforms"),
            chat_types=words("chat_types", CHAT_TYPES),
            min_response_chars=max(1, pick("min_response_chars", int)),
            start_delay=max(0.0, pick("start_delay", float)),
            script_mode=script_mode if script_mode in SCRIPT_MODES else d.script_mode,
            language=str(pick("language", str)).strip() or d.language,
            max_script_words=max(20, pick("max_script_words", int)),
            style=str(pick("style", str)).strip(),
            script_timeout=max(5.0, pick("script_timeout", float)),
            tts_provider=str(pick("tts_provider", str)).strip(),
            tts_speed=speed if speed is None or 0.25 <= speed <= 4.0 else None,
            tts_instructions=str(pick("tts_instructions", str)).strip(),
            retries=max(0, pick("retries", int)),
            notify_on_failure=pick("notify_on_failure", _to_bool),
            failure_message=str(pick("failure_message", str)) or d.failure_message,
        )


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
