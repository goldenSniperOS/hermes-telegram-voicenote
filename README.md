# hermes-telegram-voicenote

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that follows
every Telegram reply with a native **voice note** that explains the same content
in spoken form.

- The text reply is sent first and is never delayed.
- The voice note is a spoken script, not the Markdown read aloud.
- It uses the TTS provider and voice already configured in Hermes.
- Exactly one voice note per reply. Automatic Hermes work (skill review, cron,
  subagents) is not narrated.
- Silent: no confirmations in the chat. You only get a message if a voice note
  could not be produced.

See [docs/design.md](docs/design.md) for the requirements and architecture.

## Why not just use `/voice tts`?

Hermes ships a built-in voice reply mode (`/voice tts`). It is the obvious first
choice, and it is where this project started: the author enabled it on another
agent and it was not reliable enough. Sometimes a voice note arrived, sometimes it
did not. This plugin exists because of that experience.

Reading the Hermes gateway code (`_should_send_voice_reply` / `_send_voice_reply`
in `gateway/run.py`) explains the gaps:

| Built-in `/voice tts` | This plugin |
|---|---|
| Any failure is logged as a warning and the voice note is dropped. No retry, no notice. | Retries synthesis and delivery; if audio is still impossible, sends one short notice. |
| Skipped entirely when the agent called `text_to_speech` at any point in the turn. | Decides on the final reply only; one voice note per reply, guaranteed by an idempotency guard. |
| Voice-message inputs are handed to a different code path (the adapter's auto-TTS) with its own rules. | Same behavior whether you type or send audio. |
| Reads the reply aloud after stripping Markdown. Tables and lists become one flat run-on sentence. | Writes a real spoken script from the original Markdown, explaining tables and code instead of reciting them. |
| Synthesizes inside the gateway turn, before the text is finalized. | Text goes out first; audio is produced in the background. |
| Per-chat mode lives in a local state file; a chat with no explicit mode falls back to `voice.auto_tts`. | Always on for Telegram unless you turn it off with `/voicenote off`. |

The long-term hope is that this behavior becomes an option of the built-in voice
mode. Until then it lives here as a plugin, where it can evolve quickly.

> Do not enable `/voice tts` in a chat that uses this plugin, or you will get two
> audios per reply. Run `/voice off` there.

## Requirements

- Hermes Agent with the Telegram gateway configured.
- A working TTS setup in Hermes (`tts.provider`), plus `ffmpeg` for Opus output.

## Install

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --enable
```

Pin an exact release commit (recommended). Each GitHub release lists it:

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --ref <40-char-commit-sha> --enable
```

Then restart the gateway (send `/restart` from Telegram).

### Recommended configuration

Pin a fast model for the spoken script. Without it, the script is written by
your **main model**; with a large model that adds 5-10 seconds to every voice
note (the text reply is never affected):

```bash
hermes config set auxiliary.voicenote_script.provider <provider>
hermes config set auxiliary.voicenote_script.model <fast-model>
```

Use a voice that matches the script language, for example with Edge TTS:

```bash
hermes config set tts.edge.voice es-MX-DaliaNeural
```

### Checklist for a new agent

1. Install and enable the plugin, then `/restart` the gateway.
2. Pin `auxiliary.voicenote_script` to a fast model.
3. Run `/voice off` in the chat, so the built-in voice mode does not send a second audio.
4. Remove any voice-note rules from `SOUL.md`, memory, or skills. Otherwise the
   agent may also call `text_to_speech` on its own.
5. Send a message. Text arrives first; the voice note follows a few seconds later.

Found a problem? Open a **Field report** issue with the plugin version, Hermes
version, and the `telegram-voicenote` lines from `~/.hermes/logs/gateway.log`.

## Usage

The plugin works automatically. In a chat:

```
/voicenote        show status
/voicenote off    stop voice notes in this chat
/voicenote on     resume them
```

## Settings

Under `plugins.entries.telegram-voicenote.settings` in `config.yaml`:

| Key | Default | Meaning |
|---|---|---|
| `enabled` | `true` | Master switch |
| `platforms` | `[telegram]` | Platforms that receive voice notes |
| `language` | `Spanish` | Language of the spoken script |
| `max_script_words` | `180` | Upper bound for the script |
| `retries` | `2` | TTS/send retries before giving up |
| `notify_on_failure` | `true` | Send one short message only when audio is impossible |
| `script_timeout` | `90` | Seconds allowed for the script writer |
| `start_delay` | `1.5` | Seconds to wait so the text lands first |

Example:

```bash
hermes config set plugins.entries.telegram-voicenote.settings.max_script_words 120
```

## Troubleshooting

Voice notes stopped arriving? Check the gateway log:

```bash
grep telegram-voicenote ~/.hermes/logs/gateway.log | tail -20
```

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check . && pytest
hermes plugins doctor . --ci   # validates against the real Hermes runtime

# Real end-to-end run: loads the plugin through Hermes in a throwaway
# HERMES_HOME and delivers one voice note to the given chat.
~/.hermes/hermes-agent/venv/bin/python scripts/smoke_e2e.py --chat-id <telegram-chat-id>
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch model and release process.

## License

MIT
