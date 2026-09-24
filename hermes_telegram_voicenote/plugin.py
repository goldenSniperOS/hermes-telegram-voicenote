"""Plugin registration.

Scaffold only: registers the ``/voicenote`` slash command so the install,
enable, and doctor flows can be validated end to end. The voice note
behavior itself is tracked in the project issues.
"""

from __future__ import annotations

from typing import Any

COMMAND_NAME = "voicenote"


def handle_voicenote(raw_args: str = "", **_: Any) -> str:
    """Return the plugin status. Real behavior lands in a later release."""
    from . import __version__

    return f"telegram-voicenote v{__version__} is installed. Voice notes are not implemented yet."


def register(ctx: Any) -> None:
    """Entry point called by the Hermes plugin loader."""
    ctx.register_command(
        COMMAND_NAME,
        handle_voicenote,
        description="Show telegram-voicenote plugin status",
    )
