"""Hermes plugin entry point for ``hermes plugins install``.

The installer clones this repository into ``~/.hermes/plugins/telegram-voicenote``
and imports this file. The implementation lives in the
``hermes_telegram_voicenote`` package so the same code serves both the
Git install path and the pip entry-point path.
"""

from __future__ import annotations

try:  # loaded as a package by the Hermes plugin loader
    from .hermes_telegram_voicenote import __version__, register
except ImportError:  # imported flat (tests put the repo root on sys.path)
    from hermes_telegram_voicenote import __version__, register

__all__ = ["__version__", "register"]
