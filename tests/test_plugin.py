"""Behavior tests that run without a Hermes install."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

import hermes_telegram_voicenote as pkg
from hermes_telegram_voicenote.plugin import COMMAND_NAME, handle_voicenote

ROOT = Path(__file__).resolve().parent.parent


class FakeContext:
    def __init__(self) -> None:
        self.commands: dict[str, object] = {}

    def register_command(self, name, handler, description="", **_):
        self.commands[name] = handler


def test_register_adds_voicenote_command():
    ctx = FakeContext()
    pkg.register(ctx)
    assert COMMAND_NAME in ctx.commands


def test_command_reports_version():
    assert pkg.__version__ in handle_voicenote("")


def test_version_surfaces_agree():
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["version"] == pyproject["project"]["version"] == pkg.__version__


def test_manifest_name_is_filename_safe():
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", manifest["name"])
