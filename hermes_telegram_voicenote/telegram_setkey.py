"""Native Telegram wiring for /setkey.

Registered with ``ctx.register_platform_handler("telegram", ...)``, which runs
before Hermes' core handlers. The handler stops propagation
(``ApplicationHandlerStop``) so the update never reaches the gateway.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

from . import setkey

logger = logging.getLogger(__name__)

NOT_ENABLED = (
    "/setkey is disabled. Enable it on the Hermes machine with:\n"
    "hermes config set plugins.entries.telegram-voicenote.settings.setkey_enabled true"
)
DM_ONLY = "For your safety /setkey only works in a private chat with the bot."
UNAUTHORIZED = "You are not allowed to use /setkey."
DELETE_FAILED = (
    "I saved it, but I could not delete your message. Delete it yourself now: "
    "long-press it and choose Delete."
)


def _is_authorized(adapter: Any, message: Any) -> bool:
    """Fail-closed authorization, the same check Hermes uses for gated buttons."""
    user = getattr(message, "from_user", None)
    user_id = str(getattr(user, "id", "") or "").strip()
    if not user_id:
        return False
    check = getattr(adapter, "_is_callback_user_authorized", None)
    if not callable(check):
        return False
    try:
        return bool(check(user_id, chat_id=str(message.chat.id), chat_type="dm"))
    except Exception:
        logger.warning("telegram-voicenote: /setkey authorization check failed", exc_info=True)
        return False


async def handle(
    message: Any,
    adapter: Any,
    *,
    enabled: bool,
    allowed: list[str],
    writer: Callable[[str, str], None] = setkey.save_to_hermes_env,
) -> str:
    """Process one /setkey message. Returns the reply text sent to the user."""
    chat = getattr(message, "chat", None)
    if str(getattr(chat, "type", "")) != "private":
        reply = DM_ONLY
    elif not _is_authorized(adapter, message):
        reply = UNAUTHORIZED
    elif not enabled:
        reply = NOT_ENABLED
    else:
        args = (message.text or "").split()[1:]
        outcome = await asyncio.to_thread(setkey.store, args, allowed=allowed, writer=writer)
        reply = outcome.message
        if outcome.ok:
            reply += "\nRestart the gateway with /restart so every provider picks it up."

    # Always try to remove the message: it may contain a key even when rejected.
    deleted = False
    try:
        deleted = bool(await message.delete())
    except Exception:
        deleted = False
    if not deleted and len((message.text or "").split()) > 2:
        reply = f"{reply}\n\n{DELETE_FAILED}"
    await message.chat.send_message(reply)
    return reply


# Matches "/setkey", "/setkey@botname", any case. A plain regex filter is used
# instead of CommandHandler: CommandHandler needs the bot's username at match
# time, and if matching ever raised, python-telegram-bot would fall through to
# Hermes' handlers and the key would reach the gateway. The filter cannot fail.
SETKEY_PATTERN = r"(?i)^\s*/setkey(@\w+)?(\s|$)"


def make_factory(get_settings: Callable[[], Any]) -> Callable[[Any, Any], None]:
    def wire(application: Any, adapter: Any) -> None:
        from telegram.ext import ApplicationHandlerStop, MessageHandler, filters

        async def on_setkey(update: Any, context: Any) -> None:
            message = update.effective_message
            if message is None:
                raise ApplicationHandlerStop
            settings = get_settings()
            try:
                await handle(
                    message,
                    adapter,
                    enabled=settings.setkey_enabled,
                    allowed=list(settings.setkey_allowed),
                )
            except Exception:
                logger.exception("telegram-voicenote: /setkey failed")
            # Never let the update reach Hermes: that would log and store the key.
            raise ApplicationHandlerStop

        application.add_handler(
            MessageHandler(filters.Regex(SETKEY_PATTERN), on_setkey), group=-100
        )

    return wire
