"""delivery.audio_paths and live_gateway."""

from __future__ import annotations

import pytest

from hermes_telegram_voicenote import delivery


def test_audio_paths_prefers_file_paths(tmp_path):
    a, b = tmp_path / "a.ogg", tmp_path / "b.ogg"
    a.write_bytes(b"OggS"), b.write_bytes(b"OggS")
    result = {"file_path": str(a), "file_paths": [str(a), str(b)]}
    assert delivery.audio_paths(result) == [str(a), str(b)]


def test_audio_paths_falls_back_to_file_path(tmp_path):
    a = tmp_path / "a.ogg"
    a.write_bytes(b"OggS")
    assert delivery.audio_paths({"file_path": str(a)}) == [str(a)]


def test_audio_paths_rejects_missing_parts(tmp_path):
    a = tmp_path / "a.ogg"
    a.write_bytes(b"OggS")
    with pytest.raises(delivery.DeliveryError):
        delivery.audio_paths({"file_paths": [str(a), str(tmp_path / "gone.ogg")]})
    with pytest.raises(delivery.DeliveryError):
        delivery.audio_paths({})


def test_live_gateway_is_none_outside_the_gateway():
    assert delivery.live_gateway() is None


def test_missing_hermes_internal_warns_loudly(monkeypatch, caplog):
    import sys
    import types

    parent, fake = types.ModuleType("gateway"), types.ModuleType("gateway.run")
    parent.run = fake
    monkeypatch.setitem(sys.modules, "gateway", parent)
    monkeypatch.setitem(sys.modules, "gateway.run", fake)
    monkeypatch.setattr(delivery, "_warned", set())
    with caplog.at_level("ERROR"):
        assert delivery.live_gateway() is None
    assert "_gateway_runner_ref is missing" in caplog.text


def _fake_send(monkeypatch, result):
    import sys
    import types

    fake = types.ModuleType("tools.send_message_tool")

    async def _send_to_platform(*args, **kwargs):
        return result

    fake._send_to_platform = _send_to_platform
    monkeypatch.setitem(sys.modules, "tools", types.ModuleType("tools"))
    monkeypatch.setitem(sys.modules, "tools.send_message_tool", fake)
    monkeypatch.setattr(delivery, "_platform_config", lambda name: (name, None))


TARGET = delivery.Target("telegram", "123")
NOTHING_SENT = "No deliverable text or media remained after processing MEDIA tags"


def test_read_timeout_after_upload_is_ambiguous(monkeypatch):
    _fake_send(
        monkeypatch,
        {"error": NOTHING_SENT, "warnings": ["Failed to send media /tmp/a.ogg: Timed out"]},
    )
    with pytest.raises(delivery.AmbiguousDeliveryError):
        delivery.send_voice(TARGET, "/tmp/a.ogg")


@pytest.mark.parametrize(
    "reason",
    [
        "Timed out: ConnectTimeout",
        "Pool timeout: All connections in the connection pool are occupied",
        "Bad Gateway",
    ],
)
def test_failures_that_never_reached_telegram_are_retryable(monkeypatch, reason):
    _fake_send(
        monkeypatch,
        {"error": NOTHING_SENT, "warnings": [f"Failed to send media /tmp/a.ogg: {reason}"]},
    )
    with pytest.raises(delivery.DeliveryError) as info:
        delivery.send_voice(TARGET, "/tmp/a.ogg")
    assert not isinstance(info.value, delivery.AmbiguousDeliveryError)


def test_successful_send_raises_nothing(monkeypatch):
    _fake_send(monkeypatch, {"success": True, "message_id": "9"})
    delivery.send_voice(TARGET, "/tmp/a.ogg")
