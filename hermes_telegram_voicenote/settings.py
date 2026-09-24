"""Plugin settings read from ``plugins.entries.telegram-voicenote.settings``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

Getter = Callable[[str, Any], Any]


@dataclass(frozen=True)
class Settings:
    enabled: bool = True
    platforms: tuple[str, ...] = ("telegram",)
    language: str = "Spanish"
    max_script_words: int = 180
    min_response_chars: int = 1
    retries: int = 2
    notify_on_failure: bool = True
    script_timeout: float = 90.0
    start_delay: float = 1.5
    extra: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, get: Getter) -> Settings:
        defaults = cls()

        def pick(key: str, cast: Callable[[Any], Any]) -> Any:
            fallback = getattr(defaults, key)
            try:
                value = get(key, fallback)
                return fallback if value is None else cast(value)
            except (TypeError, ValueError):
                return fallback

        platforms = pick("platforms", lambda v: tuple(str(p).lower() for p in v))
        return cls(
            enabled=pick("enabled", _to_bool),
            platforms=platforms or defaults.platforms,
            language=pick("language", str),
            max_script_words=max(20, pick("max_script_words", int)),
            min_response_chars=max(1, pick("min_response_chars", int)),
            retries=max(0, pick("retries", int)),
            notify_on_failure=pick("notify_on_failure", _to_bool),
            script_timeout=max(5.0, pick("script_timeout", float)),
            start_delay=max(0.0, pick("start_delay", float)),
        )


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
