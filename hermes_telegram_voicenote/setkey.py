"""/setkey: store an API key from Telegram without it reaching the agent.

The command is wired as a native Telegram handler that runs *before* Hermes'
own handlers, so the message never enters the gateway: no agent turn, no
session transcript, no "inbound message" log line. The key is written to the
Hermes ``.env`` and the user's message is deleted from the chat.

It is off by default and restricted to private chats, authorized users, and an
explicit allowlist of credential names.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass

logger = logging.getLogger(__name__)

COMMAND = "setkey"

DEFAULT_ALLOWED = (
    "VOICE_TOOLS_OPENAI_KEY",
    "OPENAI_API_KEY",
    "ELEVENLABS_API_KEY",
    "MISTRAL_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
    "MINIMAX_API_KEY",
    "DEEPINFRA_API_KEY",
    "OPENROUTER_API_KEY",
)

# Never writable from chat, even if a user adds them to the allowlist: they
# control who can talk to the bot or which bot is running.
FORBIDDEN = frozenset(
    {
        "TELEGRAM_BOT_TOKEN",
        "TELEGRAM_ALLOWED_USERS",
        "GATEWAY_ALLOW_ALL_USERS",
        "SUDO_PASSWORD",
    }
)

_NAME = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
_CREDENTIAL_SUFFIX = re.compile(r"(_API_KEY|_KEY|_TOKEN|_SECRET)$")

USAGE = (
    "Usage: /setkey NAME value\n"
    "Example: /setkey ELEVENLABS_API_KEY sk_...\n"
    "Your message is deleted right after the key is saved."
)


@dataclass(frozen=True)
class Outcome:
    ok: bool
    message: str
    name: str = ""


def mask(value: str) -> str:
    tail = value[-4:] if len(value) >= 12 else ""
    return f"...{tail}" if tail else "(hidden)"


def parse(args: Iterable[str]) -> tuple[str, str] | None:
    parts = [a for a in args if a]
    if len(parts) != 2:
        return None
    return parts[0].strip().upper(), parts[1].strip()


def check_name(name: str, allowed: Iterable[str]) -> str | None:
    """Return an error message, or None when *name* may be written."""
    if not _NAME.match(name) or not _CREDENTIAL_SUFFIX.search(name):
        return (
            f"{name} is not a credential name (it must end in _API_KEY, _KEY, _TOKEN, or _SECRET)."
        )
    if name in FORBIDDEN:
        return f"{name} cannot be changed from the chat."
    if name not in {a.upper() for a in allowed}:
        return (
            f"{name} is not in the allowlist. Add it to "
            "plugins.entries.telegram-voicenote.settings.setkey_allowed first."
        )
    return None


def store(
    args: Iterable[str],
    *,
    allowed: Iterable[str],
    writer: Callable[[str, str], None],
) -> Outcome:
    parsed = parse(args)
    if parsed is None:
        return Outcome(False, USAGE)
    name, value = parsed
    error = check_name(name, allowed)
    if error:
        return Outcome(False, error, name)
    if len(value) < 8 or any(c.isspace() for c in value):
        return Outcome(False, "That value does not look like an API key.", name)
    try:
        writer(name, value)
    except Exception as exc:
        # Never include the value, and never the exception text (it could echo it).
        logger.error("telegram-voicenote: /setkey could not save %s (%s)", name, type(exc).__name__)
        return Outcome(False, f"Could not save {name} ({type(exc).__name__}).", name)
    logger.info("telegram-voicenote: /setkey saved %s", name)
    return Outcome(True, f"Saved {name} ({mask(value)}).", name)


def save_to_hermes_env(name: str, value: str) -> None:
    """Persist through Hermes' own credential path, then apply it to this process."""
    import os

    from hermes_cli.credential_lifecycle import save_provider_env_credential

    save_provider_env_credential(name, value)
    os.environ[name] = value
