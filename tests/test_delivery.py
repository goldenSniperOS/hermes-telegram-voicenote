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
