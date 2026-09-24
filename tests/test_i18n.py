"""Language helpers."""

from __future__ import annotations

from hermes_telegram_voicenote import i18n
from hermes_telegram_voicenote.settings import Settings

TTS = {"provider": "edge", "edge": {"voice": "en-US-AriaNeural"}}


def test_failure_message_follows_language():
    s = Settings.load(lambda k, d: {"language": "Spanish"}.get(k, d))
    assert s.failure_message.startswith("No pude generar")
    assert Settings.load(lambda k, d: d).failure_message.startswith("I could not")


def test_custom_failure_message_wins():
    cfg = {"language": "Spanish", "failure_message": "Sin audio ({reason})"}
    assert Settings.load(lambda k, d: cfg.get(k, d)).failure_message == "Sin audio ({reason})"


def test_mismatch_detected_for_pinned_language():
    assert "sound wrong" in i18n.mismatch("Spanish", TTS)


def test_no_mismatch_for_auto_matching_or_unknown_voice():
    assert i18n.mismatch("auto", TTS) == ""
    assert i18n.mismatch("English", TTS) == ""
    assert (
        i18n.mismatch("Spanish", {"provider": "edge", "edge": {"voice": "es-MX-DaliaNeural"}}) == ""
    )
    assert i18n.mismatch("Spanish", {"provider": "openai", "openai": {"voice": "alloy"}}) == ""


def test_plugin_tts_provider_is_the_one_checked():
    tts = {
        "provider": "edge",
        "edge": {"voice": "es-MX-DaliaNeural"},
        "azure": {"voice": "en-US-Jenny"},
    }
    assert "azure" in i18n.mismatch("Spanish", tts, "azure")
