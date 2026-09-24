"""Pipeline behavior tests with fake host ports."""

from __future__ import annotations

import pytest

from hermes_telegram_voicenote.delivery import Target
from hermes_telegram_voicenote.guard import DedupGuard
from hermes_telegram_voicenote.pipeline import Ports, VoiceNotePipeline
from hermes_telegram_voicenote.script import fallback_script, make_script
from hermes_telegram_voicenote.settings import Settings

TG = Target("telegram", "123")


class Host:
    def __init__(self, target=TG, review=False, fail_times=0, writer="Guion hablado."):
        self.target, self.review, self.fail_times = target, review, fail_times
        self.voices, self.texts, self.scripts, self.threads = [], [], [], []
        self.writer_output = writer

    def ports(self):
        return Ports(
            resolve_target=lambda: self.target,
            is_background_review=lambda: self.review,
            synthesize=self._synth,
            send_voice=lambda t, p: self.voices.append((t, p)),
            send_text=lambda t, m: self.texts.append((t, m)),
            script_writer=self._write,
        )

    def _write(self, messages, timeout):
        if isinstance(self.writer_output, Exception):
            raise self.writer_output
        return self.writer_output

    def _synth(self, script):
        self.scripts.append(script)
        if self.fail_times:
            self.fail_times -= 1
            raise RuntimeError("tts down")
        return "/tmp/a.ogg"


def make(host, settings=None, muted=False):
    return VoiceNotePipeline(
        settings=lambda: settings or Settings(),
        ports=host.ports(),
        is_muted=lambda t: muted,
        start_thread=lambda fn: fn(),
        sleep=lambda s: None,
    )


def test_returns_none_and_delivers_one_voice_note():
    host = Host()
    assert make(host).on_llm_output(response_text="Hola **mundo**", platform="telegram") is None
    assert host.voices == [(TG, "/tmp/a.ogg")]
    assert host.scripts == ["Guion hablado."]
    assert host.texts == []


def test_work_is_deferred_to_a_thread():
    host = Host()
    started = []
    pipe = VoiceNotePipeline(lambda: Settings(), host.ports(), start_thread=started.append)
    pipe.on_llm_output(response_text="hola", platform="telegram")
    assert host.voices == [] and len(started) == 1


def test_same_reply_is_voiced_only_once():
    host = Host()
    pipe = make(host)
    pipe.on_llm_output(response_text="hola ", platform="telegram")
    pipe.on_llm_output(response_text="hola", platform="telegram")
    assert len(host.voices) == 1


@pytest.mark.parametrize(
    "host_kwargs,text,platform",
    [
        ({"review": True}, "skill improved", "telegram"),
        ({"target": None}, "hola", "cli"),
        ({"target": Target("discord", "1")}, "hola", "discord"),
        ({}, "", "telegram"),
        ({}, "[[audio_as_voice]]\nMEDIA:/x.ogg", "telegram"),
    ],
)
def test_skips_what_is_not_a_user_facing_telegram_reply(host_kwargs, text, platform):
    host = Host(**host_kwargs)
    make(host).on_llm_output(response_text=text, platform=platform)
    assert host.voices == [] and host.texts == []


def test_muted_chat_is_skipped():
    host = Host()
    make(host, muted=True).on_llm_output(response_text="hola", platform="telegram")
    assert host.voices == []


def test_disabled_setting_is_respected():
    host = Host()
    make(host, Settings(enabled=False)).on_llm_output(response_text="hola", platform="telegram")
    assert host.voices == []


def test_retries_then_succeeds_silently():
    host = Host(fail_times=2)
    make(host, Settings(retries=2)).on_llm_output(response_text="hola", platform="telegram")
    assert len(host.voices) == 1 and host.texts == []


def test_notifies_only_when_audio_is_impossible():
    host = Host(fail_times=10)
    make(host, Settings(retries=1)).on_llm_output(response_text="hola", platform="telegram")
    assert host.voices == [] and len(host.texts) == 1


def test_script_writer_failure_falls_back_to_cleaned_text():
    host = Host(writer=RuntimeError("model down"))
    make(host).on_llm_output(response_text="## Titulo\n**hola** mundo", platform="telegram")
    assert len(host.voices) == 1
    assert "**" not in host.scripts[0] and "##" not in host.scripts[0]


def test_make_script_without_writer_uses_fallback():
    out = make_script("`code` y **texto**", None, language="Spanish", max_words=50, timeout=5)
    assert "`" not in out and "**" not in out


def test_fallback_respects_word_limit():
    assert len(fallback_script("uno " * 500, max_words=10).split()) == 10


def test_guard_capacity_is_bounded():
    guard = DedupGuard(capacity=2)
    for i in range(3):
        assert guard.claim("t", str(i))
    assert guard.claim("t", "0")  # evicted, so accepted again


def test_settings_load_tolerates_bad_values():
    raw = {"retries": "x", "platforms": ["Telegram"], "enabled": "off"}
    s = Settings.load(lambda k, d: raw.get(k, d))
    assert s.retries == Settings().retries
    assert s.platforms == ("telegram",)
    assert s.enabled is False
