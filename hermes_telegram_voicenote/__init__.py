"""Telegram voice note plugin for Hermes Agent."""

from __future__ import annotations

__version__ = "0.3.0"

from .plugin import register  # noqa: E402

__all__ = ["__version__", "register"]
