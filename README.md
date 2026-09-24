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

Pin a fast model for the spoken script, so a slow main model does not delay it:

```bash
hermes config set auxiliary.voicenote_script.provider <provider>
hermes config set auxiliary.voicenote_script.model <fast-model>
```

Use a voice that matches the script language, for example with Edge TTS:

```bash
hermes config set tts.edge.voice es-MX-DaliaNeural
```

If you previously added voice-note rules to `SOUL.md`, memory, or a skill,
remove them. Otherwise the agent may also send its own audio.

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
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch model and release process.

## License

MIT
