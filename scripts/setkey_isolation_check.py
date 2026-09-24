"""Prove /setkey never reaches Hermes' own Telegram handlers.

Builds a real python-telegram-bot Application, registers the plugin factory the
way the Telegram adapter does (plugin factories first, then the core handlers),
feeds it a real /setkey Update, and asserts that:

  * the key was written,
  * the core Hermes command handler never saw the update,
  * a normal command (/status) still reaches the core handler.

No network: the bot's delete/send calls are replaced with recorders.

Usage (run with the Hermes interpreter):

    ~/.hermes/hermes-agent/venv/bin/python scripts/setkey_isolation_check.py
"""

from __future__ import annotations

import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

KEY = "sk-isolation-check-0000000000"


async def main() -> int:
    from telegram import Chat, Message, Update, User
    from telegram.ext import ApplicationBuilder, MessageHandler, filters

    from hermes_telegram_voicenote import telegram_setkey
    from hermes_telegram_voicenote.settings import Settings

    written: dict[str, str] = {}
    core_seen: list[str] = []
    replies: list[str] = []

    class Adapter:
        def _is_callback_user_authorized(self, user_id, **_):
            return user_id == "7"

    app = ApplicationBuilder().token("123:TEST").updater(None).build()

    # 1. Plugin factories are wired first, exactly like the Telegram adapter does.
    original_handle = telegram_setkey.handle

    async def recording_handle(message, adapter, **kw):
        kw["writer"] = written.__setitem__
        return await original_handle(message, adapter, **kw)

    telegram_setkey.handle = recording_handle
    settings = Settings(setkey_enabled=True)
    telegram_setkey.make_factory(lambda: settings)(app, Adapter())

    # 2. Then Hermes' core handlers (same filters the adapter registers).
    async def core(update, context):
        core_seen.append(update.effective_message.text)

    app.add_handler(MessageHandler(filters.COMMAND, core))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, core))

    chat = Chat(id=7, type="private")
    user = User(id=7, first_name="Owner", is_bot=False)

    def update_for(text: str, update_id: int) -> Update:
        entity_len = len(text.split()[0])
        from telegram import MessageEntity

        msg = Message(
            message_id=update_id,
            date=datetime.now(UTC),
            chat=chat,
            from_user=user,
            text=text,
            entities=[MessageEntity(MessageEntity.BOT_COMMAND, 0, entity_len)],
        )
        return Update(update_id=update_id, message=msg)

    async def fake_delete(self, *a, **k):
        return True

    async def fake_send(self, text, *a, **k):
        replies.append(text)

    Message.delete = fake_delete
    Chat.send_message = fake_send

    # initialize() would call getMe on Telegram; stub the bot's network init only.
    async def _no_network(*_a, **_k):
        return None

    from telegram.ext import ExtBot

    ExtBot.initialize = _no_network
    ExtBot.shutdown = _no_network
    await app.initialize()
    cases = [
        f"/setkey OPENAI_API_KEY {KEY}",
        f"/SetKey@my_bot OPENAI_API_KEY {KEY}",
        "/status",
    ]
    for i, text in enumerate(cases, start=1):
        upd = update_for(text, i)
        upd.set_bot(app.bot)
        upd.message.set_bot(app.bot)
        await app.process_update(upd)

    await app.shutdown()
    leaked = any(KEY in t for t in core_seen) or any(KEY in r for r in replies)
    print(f"written: {sorted(written)} (2 setkey messages)")
    print(f"core handler saw: {core_seen}")
    print(f"bot replies: {replies}")
    ok = written == {"OPENAI_API_KEY": KEY} and core_seen == ["/status"] and not leaked
    print("isolation:", "OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
