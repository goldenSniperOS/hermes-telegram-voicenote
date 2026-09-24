"""/setkey behavior: validation, masking, and the Telegram gate."""

from __future__ import annotations

import asyncio

import pytest

from hermes_telegram_voicenote import setkey, telegram_setkey
from hermes_telegram_voicenote.settings import Settings

KEY = "sk-test-1234567890abcdef"


def run(coro):
    return asyncio.run(coro)


def test_store_writes_allowed_key_and_masks_it():
    saved = {}
    out = setkey.store(
        ["ELEVENLABS_API_KEY", KEY],
        allowed=setkey.DEFAULT_ALLOWED,
        writer=saved.__setitem__,
    )
    assert out.ok and saved == {"ELEVENLABS_API_KEY": KEY}
    assert KEY not in out.message and "...cdef" in out.message


def test_name_is_normalized_to_upper_case():
    saved = {}
    setkey.store(
        ["elevenlabs_api_key", KEY], allowed=setkey.DEFAULT_ALLOWED, writer=saved.__setitem__
    )
    assert "ELEVENLABS_API_KEY" in saved


@pytest.mark.parametrize(
    "args,reason",
    [
        (["ELEVENLABS_API_KEY"], "Usage"),
        (["ELEVENLABS_API_KEY", KEY, "extra"], "Usage"),
        (["PATH", "/usr/bin/evil"], "not a credential name"),
        (["TELEGRAM_BOT_TOKEN", KEY], "cannot be changed"),
        (["GATEWAY_ALLOW_ALL_USERS_TOKEN", KEY], "not in the allowlist"),
        (["ELEVENLABS_API_KEY", "short"], "does not look like"),
    ],
)
def test_store_rejects_unsafe_input(args, reason):
    saved = {}
    out = setkey.store(args, allowed=setkey.DEFAULT_ALLOWED, writer=saved.__setitem__)
    assert not out.ok and reason in out.message and not saved


def test_forbidden_names_stay_forbidden_even_if_allowlisted():
    out = setkey.store(
        ["TELEGRAM_BOT_TOKEN", KEY], allowed=["TELEGRAM_BOT_TOKEN"], writer=lambda k, v: None
    )
    assert not out.ok


def test_writer_errors_never_echo_the_value():
    def boom(name, value):
        raise OSError(f"disk full while writing {value}")

    out = setkey.store(["OPENAI_API_KEY", KEY], allowed=setkey.DEFAULT_ALLOWED, writer=boom)
    assert not out.ok and KEY not in out.message and "OSError" in out.message


def test_settings_default_off_and_default_allowlist():
    assert Settings().setkey_allowed == setkey.DEFAULT_ALLOWED
    s = Settings.load(lambda k, d: d)
    assert s.setkey_enabled is False and s.setkey_allowed == setkey.DEFAULT_ALLOWED
    s = Settings.load(lambda k, d: {"setkey_allowed": "foo_api_key, BAR_TOKEN"}.get(k, d))
    assert s.setkey_allowed == ("FOO_API_KEY", "BAR_TOKEN")


# -- Telegram gate -------------------------------------------------------------


class Chat:
    def __init__(self, type_="private"):
        self.type, self.id, self.sent = type_, 42, []

    async def send_message(self, text):
        self.sent.append(text)


class User:
    id = 7


class Message:
    def __init__(self, text, chat=None, can_delete=True):
        self.text, self.chat, self.from_user = text, chat or Chat(), User()
        self.can_delete, self.deleted = can_delete, False

    async def delete(self):
        if not self.can_delete:
            raise RuntimeError("no rights")
        self.deleted = True
        return True


class Adapter:
    def __init__(self, allowed=True):
        self.allowed = allowed

    def _is_callback_user_authorized(self, user_id, **_):
        return self.allowed


def handle(msg, adapter=None, enabled=True):
    saved = {}
    reply = run(
        telegram_setkey.handle(
            msg,
            adapter or Adapter(),
            enabled=enabled,
            allowed=list(setkey.DEFAULT_ALLOWED),
            writer=saved.__setitem__,
        )
    )
    return reply, saved


def test_gate_saves_and_deletes_the_message():
    msg = Message(f"/setkey OPENAI_API_KEY {KEY}")
    reply, saved = handle(msg)
    assert saved == {"OPENAI_API_KEY": KEY} and msg.deleted
    assert KEY not in reply and KEY not in msg.chat.sent[0]


@pytest.mark.parametrize(
    "msg,adapter,enabled,expected",
    [
        (Message(f"/setkey OPENAI_API_KEY {KEY}", Chat("group")), None, True, "private chat"),
        (Message(f"/setkey OPENAI_API_KEY {KEY}"), Adapter(allowed=False), True, "not allowed"),
        (Message(f"/setkey OPENAI_API_KEY {KEY}"), None, False, "disabled"),
    ],
)
def test_gate_refuses_but_still_deletes(msg, adapter, enabled, expected):
    reply, saved = handle(msg, adapter, enabled)
    assert expected in reply and not saved and msg.deleted


def test_gate_warns_when_message_cannot_be_deleted():
    msg = Message(f"/setkey OPENAI_API_KEY {KEY}", can_delete=False)
    reply, saved = handle(msg)
    assert saved and "could not delete" in reply


def test_adapter_without_auth_check_fails_closed():
    class Bare:
        pass

    msg = Message(f"/setkey OPENAI_API_KEY {KEY}")
    reply, saved = handle(msg, Bare())
    assert "not allowed" in reply and not saved


@pytest.mark.parametrize(
    "text,matches",
    [
        ("/setkey OPENAI_API_KEY x", True),
        ("/SETKEY OPENAI_API_KEY x", True),
        ("/setkey@my_bot OPENAI_API_KEY x", True),
        ("  /setkey OPENAI_API_KEY x", True),
        ("/setkey", True),
        ("/setkeys foo", False),
        ("/status", False),
        ("please /setkey later", False),
    ],
)
def test_setkey_pattern_catches_every_form(text, matches):
    import re

    assert bool(re.search(telegram_setkey.SETKEY_PATTERN, text)) is matches
