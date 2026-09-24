"""Plugin registration and host wiring."""

from __future__ import annotations

import logging
from typing import Any

from . import delivery
from .delivery import Target
from .guard import process_guard
from .pipeline import Ports, VoiceNotePipeline
from .settings import Settings

logger = logging.getLogger(__name__)

PLUGIN_ID = "telegram-voicenote"
COMMAND_NAME = "voicenote"
SCRIPT_TASK = "voicenote_script"
MUTED_KEY = "muted_targets"


def _resolve_target() -> Target | None:
    try:
        from gateway.session_context import get_session_env
    except Exception:
        return None
    platform = get_session_env("HERMES_SESSION_PLATFORM", "").lower()
    chat_id = get_session_env("HERMES_SESSION_CHAT_ID", "")
    if not platform or not chat_id or get_session_env("HERMES_CRON_SESSION", ""):
        return None
    chat_type = (get_session_env("HERMES_SESSION_CHAT_TYPE", "") or "dm").lower()
    if chat_type in {"private", "direct"}:
        chat_type = "dm"
    elif chat_type in {"supergroup", "channel"}:
        chat_type = "group"
    return Target(
        platform,
        chat_id,
        get_session_env("HERMES_SESSION_THREAD_ID", ""),
        chat_type,
    )


def _gateway_is_live() -> bool:
    return delivery.live_gateway() is not None


def _is_background_review() -> bool:
    try:
        from tools.skill_provenance import is_background_review

        return is_background_review()
    except Exception:
        return False


def _script_writer(ctx: Any):
    def write(messages: list[dict[str, str]], timeout: float) -> str:
        result = ctx.llm.complete(
            messages=messages,
            task=SCRIPT_TASK,
            timeout=timeout,
            purpose="telegram-voicenote script",
        )
        return result.text

    return write


class _MuteStore:
    def __init__(self, ctx: Any) -> None:
        self._ctx = ctx

    def _all(self) -> list[str]:
        try:
            return list(self._ctx.state.get(MUTED_KEY, []) or [])
        except Exception:
            return []

    def is_muted(self, target: Target) -> bool:
        return target.key in self._all()

    def set(self, target: Target, muted: bool) -> None:
        keys = set(self._all())
        (keys.add if muted else keys.discard)(target.key)
        self._ctx.state.set(MUTED_KEY, sorted(keys))


def _script_model(ctx: Any) -> str:
    """The pinned script model, or 'main' when the slot falls back to it."""
    try:
        from hermes_cli.config import load_config

        slot = (load_config().get("auxiliary") or {}).get(SCRIPT_TASK) or {}
    except Exception:
        return "unknown"
    model = str(slot.get("model") or "").strip()
    provider = str(slot.get("provider") or "").strip()
    if not model or provider in {"", "auto"} and not model:
        return "main (unpinned)"
    return f"{provider}/{model}" if provider and provider != "auto" else model


def make_command(ctx: Any, mutes: _MuteStore):
    from . import __version__

    def handle(raw_args: str = "", **_: Any) -> str:
        arg = (raw_args or "").strip().lower()
        target = _resolve_target()
        if arg in {"on", "off"}:
            if target is None:
                return "Voice notes can only be toggled from a chat."
            mutes.set(target, arg == "off")
            return f"Voice notes {'disabled' if arg == 'off' else 'enabled'} for this chat."
        s = Settings.load(ctx.get_config)
        here = "n/a" if target is None else ("off" if mutes.is_muted(target) else "on")
        return "\n".join(
            [
                f"telegram-voicenote v{__version__}: "
                f"{'enabled' if s.enabled else 'disabled'} globally, {here} in this chat.",
                f"script={s.script_mode} model={_script_model(ctx)} language={s.language} "
                f"max_words={s.max_script_words} style={'set' if s.style else 'none'}",
                f"tts={s.tts_provider or 'default'} speed={s.tts_speed or 'default'} "
                f"retries={s.retries} start_delay={s.start_delay}s",
                f"chats={','.join(s.chat_types)} min_chars={s.min_response_chars} "
                f"setkey={'on' if s.setkey_enabled else 'off'}",
                "Usage: /voicenote [on|off]",
            ]
        )

    return handle


def register(ctx: Any) -> None:
    """Entry point called by the Hermes plugin loader."""
    try:
        ctx.register_auxiliary_task(
            SCRIPT_TASK,
            display_name="Voice note script",
            description="Rewrites replies as a spoken script for telegram-voicenote",
            defaults={"provider": "auto", "timeout": 90},
        )
        writer = _script_writer(ctx)
    except Exception as exc:
        logger.warning("telegram-voicenote: auxiliary task unavailable (%s)", exc)
        writer = None

    mutes = _MuteStore(ctx)
    pipeline = VoiceNotePipeline(
        settings=lambda: Settings.load(ctx.get_config),
        ports=Ports(
            resolve_target=_resolve_target,
            is_background_review=_is_background_review,
            gateway_is_live=_gateway_is_live,
            synthesize=delivery.synthesize,
            send_voice=delivery.send_voice,
            send_text=delivery.send_text,
            script_writer=writer,
        ),
        is_muted=mutes.is_muted,
        guard=process_guard(),
    )
    ctx.register_hook("transform_llm_output", pipeline.on_llm_output)
    if _script_model(ctx) == "main (unpinned)":
        logger.warning(
            "telegram-voicenote: auxiliary.%s is not pinned; scripts use the main "
            "model, which can add many seconds per voice note on a large model",
            SCRIPT_TASK,
        )
    try:
        from .telegram_setkey import make_factory

        ctx.register_platform_handler(
            "telegram", make_factory(lambda: Settings.load(ctx.get_config))
        )
    except Exception as exc:
        logger.warning("telegram-voicenote: /setkey unavailable (%s)", exc)
    ctx.register_command(
        COMMAND_NAME,
        make_command(ctx, mutes),
        description="Show or toggle Telegram voice notes for this chat",
        args_hint="[on|off]",
    )
