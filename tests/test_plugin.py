"""Registration and manifest tests."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

import hermes_telegram_voicenote as pkg
from hermes_telegram_voicenote.plugin import COMMAND_NAME, SCRIPT_TASK

ROOT = Path(__file__).resolve().parent.parent


class FakeState:
    def __init__(self):
        self.data = {}

    def get(self, key, default=None):
        return self.data.get(key, default)

    def set(self, key, value):
        self.data[key] = value


class FakeContext:
    def __init__(self, settings=None):
        self.commands, self.hooks, self.tasks = {}, {}, {}
        self.settings = settings or {}
        self.state = FakeState()

    def register_command(self, name, handler, description="", **_):
        self.commands[name] = handler

    def register_hook(self, name, cb):
        self.hooks[name] = cb

    def register_auxiliary_task(self, key, **kw):
        self.tasks[key] = kw

    def register_platform_handler(self, platform, factory):
        self.platform_handlers = getattr(self, "platform_handlers", {})
        self.platform_handlers[platform] = factory

    def get_config(self, key, default=None):
        return self.settings.get(key, default)


def test_register_wires_hook_command_and_script_task():
    ctx = FakeContext()
    pkg.register(ctx)
    assert COMMAND_NAME in ctx.commands
    assert "transform_llm_output" in ctx.hooks
    assert SCRIPT_TASK in ctx.tasks
    assert "telegram" in ctx.platform_handlers


def test_hook_never_replaces_the_reply():
    ctx = FakeContext()
    pkg.register(ctx)
    assert ctx.hooks["transform_llm_output"](response_text="hello", platform="telegram") is None


def test_status_command_reports_version():
    ctx = FakeContext()
    pkg.register(ctx)
    assert pkg.__version__ in ctx.commands[COMMAND_NAME]("")


def test_version_surfaces_agree():
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert manifest["version"] == pyproject["project"]["version"] == pkg.__version__


def test_manifest_name_is_filename_safe():
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert re.fullmatch(r"[a-z0-9][a-z0-9-]*", manifest["name"])


def test_manifest_version_is_installable():
    # The Hermes Git installer rejects manifest_version > 1 (verified on v0.21.0),
    # even though `hermes plugins doctor` accepts it.
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert manifest.get("manifest_version", 1) == 1


def test_manifest_declares_the_hook():
    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    assert "transform_llm_output" in manifest["provides_hooks"]


def test_every_setting_is_documented_in_the_manifest_and_readme():
    from dataclasses import fields

    from hermes_telegram_voicenote.settings import Settings

    manifest = yaml.safe_load((ROOT / "plugin.yaml").read_text())
    readme = (ROOT / "README.md").read_text()
    for f in fields(Settings):
        assert f.name in manifest["config_schema"], f"{f.name} missing from plugin.yaml"
        assert f"`{f.name}`" in readme, f"{f.name} missing from README"


def test_double_registration_voices_a_reply_once(monkeypatch):
    import sys

    from hermes_telegram_voicenote import plugin as plugin_mod
    from hermes_telegram_voicenote.delivery import Target

    monkeypatch.delattr(sys, "_telegram_voicenote_guard", raising=False)
    sent = []
    monkeypatch.setattr(plugin_mod, "_resolve_target", lambda: Target("telegram", "1"))
    monkeypatch.setattr(plugin_mod.delivery, "synthesize", lambda s, **k: "/tmp/a.ogg")
    monkeypatch.setattr(plugin_mod.delivery, "send_voice", lambda t, p: sent.append(t))
    monkeypatch.setattr("hermes_telegram_voicenote.pipeline._daemon", lambda fn: fn())
    monkeypatch.setattr("hermes_telegram_voicenote.pipeline.time.sleep", lambda s: None)

    first, second = FakeContext({"script_mode": "plain"}), FakeContext({"script_mode": "plain"})
    pkg.register(first)
    pkg.register(second)
    for ctx in (first, second):
        ctx.hooks["transform_llm_output"](response_text="same reply", platform="telegram")
    assert len(sent) == 1
