# hermes-telegram-voicenote

**Listen to your AI agent instead of reading it.**

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that follows
every Telegram reply with a native **voice note** that explains the same answer in
spoken form.

## Why this exists

Hermes is great at long, structured answers: analyses, tables, code reviews, plans.
That is exactly what is hard to consume on a phone. You are walking, driving, cooking,
or between meetings. You typed a question or sent a voice note, and what comes back is
a wall of Markdown on a five-inch screen.

This plugin gives you a second way to take in every answer:

- **The text arrives first, immediately.** Nothing waits for audio.
- **A voice note follows a few seconds later.** Tap play and put the phone in your pocket.
- **It is a spoken explanation, not a robot reading Markdown.** Tables, lists, and code
  are explained in plain words ("the build passed and the release is published") instead
  of recited cell by cell.

Read when you can, listen when you cannot. Both are always there.

## Why not the alternatives?

### Hermes' built-in `/voice tts`

Hermes ships a voice reply mode, and it is where this project started: it was enabled on
a real agent and was not reliable enough. Sometimes a voice note arrived, sometimes it
did not. Reading the gateway code (`_should_send_voice_reply` / `_send_voice_reply` in
`gateway/run.py`) explains why:

| Built-in `/voice tts` | This plugin |
|---|---|
| Any failure is logged and the voice note is silently dropped. No retry, no notice. | Retries synthesis and delivery; if audio is still impossible, you get one short notice. |
| Skipped entirely when the agent called `text_to_speech` at any point in the turn. | Decides on the final reply only; exactly one voice note per reply. |
| Voice-message inputs take a different code path with different rules. | Same behavior whether you type or talk. |
| Reads the reply after stripping Markdown. Tables and lists become one flat run-on sentence. | Writes a real spoken script from the original Markdown. |
| Synthesizes inside the gateway turn. | Text goes out first; audio is produced in the background. |

> Do not enable `/voice tts` in a chat that uses this plugin, or you will get two audios
> per reply. Run `/voice off` there.

### Other plugins

Existing voice plugins solve a different problem. Engine swaps (for example local or
cloned voices) change *how* audio is synthesized, and language routers pick a voice per
language; neither decides to send a voice note after every reply. Script shorteners built
as TTS providers receive the text **after** Hermes has already flattened the Markdown,
so they cannot explain tables or lists properly, and they still depend on the built-in
trigger above. These plugins are complementary: this plugin uses whatever TTS provider
you configure, including plugin providers.

The long-term hope is that this behavior becomes an option of Hermes' built-in voice
mode. Until then it lives here, where it can evolve quickly from real use.

## How it works

```
reply finishes ─► text is sent now (never modified, never delayed)
                └► background worker:
                     1. write a spoken script   (your chosen model, or plain cleanup)
                     2. synthesize              (your Hermes TTS provider and voice)
                     3. send as a voice note    (native Telegram bubble, with retries)
```

It skips what is not a real answer to you: Hermes' automatic skill/memory review, cron
jobs, and subagents are never narrated. See [docs/design.md](docs/design.md) for details.

## Requirements

- Hermes Agent with the Telegram gateway configured.
- A working TTS provider in Hermes (the free default, Edge TTS, works out of the box).
- `ffmpeg`, so audio can be converted to Telegram's Opus voice format.

## Install

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --enable
```

For a reproducible install, pin the release commit listed on each
[GitHub release](https://github.com/goldenSniperOS/hermes-telegram-voicenote/releases):

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --ref <commit-sha> --enable
```

Restart the gateway (send `/restart` in Telegram), then send any message.

### Setup checklist

1. Install and enable the plugin, then `/restart`.
2. **Pick a fast model for the script** (see below). Without it the script is written by
   your main model; a large model can add 5–10 seconds per voice note. The text reply is
   never affected.
3. Choose a TTS voice that matches the language you talk in (see below).
4. Run `/voice off` in the chat so the built-in voice mode does not send a second audio.
5. If you ever added "always send a voice note" rules to `SOUL.md`, memory, or a skill,
   remove them. The plugin owns this now.

## Configuration

Everything is optional. With no configuration, the plugin sends voice notes in every
Telegram chat, writes the script with your main model in the same language as the reply,
and uses your global Hermes TTS voice.

### 1. The script model

The spoken script is written through the plugin's own auxiliary model slot,
`voicenote_script`. Pick any provider and model Hermes supports:

```bash
hermes config set auxiliary.voicenote_script.provider openrouter
hermes config set auxiliary.voicenote_script.model google/gemini-3-flash
```

It also appears in `hermes model` → *Configure auxiliary models...*. Prefer something fast
and inexpensive; the task is short rewriting.

Do not want an LLM involved at all? Use plain mode, which speaks a cleaned-up version of
the reply (no extra model call, no extra cost):

```bash
hermes config set plugins.entries.telegram-voicenote.settings.script_mode plain
```

### 2. The voice

By default the plugin uses your global Hermes TTS settings (`tts.*`). For example, with
the free Edge TTS provider:

```bash
hermes config set tts.edge.voice en-US-AriaNeural   # English
hermes config set tts.edge.voice es-MX-DaliaNeural  # Spanish
hermes config set tts.edge.voice de-DE-KatjaNeural  # German
```

To use a different provider, speed, or delivery style **only for voice notes**, without
changing the rest of Hermes:

```bash
hermes config set plugins.entries.telegram-voicenote.settings.tts_provider openai
hermes config set plugins.entries.telegram-voicenote.settings.tts_speed 1.15
hermes config set plugins.entries.telegram-voicenote.settings.tts_instructions "Calm, friendly, unhurried"
```

`tts_instructions` is honored by providers that support voice direction (such as
OpenAI `gpt-4o-mini-tts`) and ignored by the rest.

### 3. All settings

Set with `hermes config set plugins.entries.telegram-voicenote.settings.<key> <value>`,
or edit `config.yaml`:

```yaml
plugins:
  entries:
    telegram-voicenote:
      settings:
        enabled: true
        chat_types: [dm, group, forum]
        script_mode: llm
        language: auto
        max_script_words: 180
        style: ""
        tts_provider: ""
        retries: 2
        notify_on_failure: true
```

| Key | Default | What it does |
|---|---|---|
| **When** | | |
| `enabled` | `true` | Master switch for every chat. |
| `platforms` | `[telegram]` | Platforms that receive voice notes. Telegram is the supported target. |
| `chat_types` | `[dm, group, forum]` | Which chats get voice notes. Use `[dm]` to keep groups quiet. |
| `min_response_chars` | `1` | Skip replies shorter than this, for example `200` to voice only longer answers. |
| `start_delay` | `1.5` | Seconds to wait so the text lands before the audio. |
| **What** | | |
| `script_mode` | `llm` | `llm` writes a spoken explanation; `plain` speaks a cleaned-up reply with no model call. |
| `language` | `auto` | `auto` speaks in the language of the reply; or name one, such as `English` or `Spanish`. |
| `max_script_words` | `180` | Upper bound for the script. About 150 words is one minute of audio. |
| `style` | *(empty)* | Extra instructions for the script writer, for example `"Be brief and casual."` |
| `script_timeout` | `90` | Seconds allowed for the script model before falling back to plain mode. |
| **How it sounds** | | |
| `tts_provider` | *(global)* | TTS provider for voice notes only, for example `openai`, `elevenlabs`, `edge`. |
| `tts_speed` | *(global)* | Playback speed from `0.25` to `4.0`. |
| `tts_instructions` | *(empty)* | Voice direction for providers that support it. |
| **Reliability** | | |
| `retries` | `2` | Extra attempts when synthesis or delivery fails. |
| `notify_on_failure` | `true` | Send one short message only when a voice note is impossible. |
| `failure_message` | *(English)* | Text of that message. `{reason}` is replaced with the error type. |

### Per chat

```
/voicenote        show the current status and settings
/voicenote off    stop voice notes in this chat
/voicenote on     resume them
```

## Troubleshooting

| Symptom | Check |
|---|---|
| No voice note at all | `hermes plugins list` shows `enabled`; you ran `/restart`; `/voicenote` says `on`. |
| Voice note arrives as a file | Install `ffmpeg` so audio can be converted to Opus. |
| Two audios per reply | Run `/voice off`, and remove voice rules from `SOUL.md` or memory. |
| Voice notes are slow | Pin a fast model in `auxiliary.voicenote_script`, or use `script_mode: plain`. |
| Wrong accent | Pick a TTS voice for your language (`tts.edge.voice`, or `tts_provider`). |

Logs:

```bash
grep telegram-voicenote ~/.hermes/logs/gateway.log | tail -20
```

Still stuck, or it misbehaved on a real agent? Open a
[Field report](https://github.com/goldenSniperOS/hermes-telegram-voicenote/issues/new/choose).

## Security and privacy

- Plugins run inside Hermes with its permissions. Review the code before enabling it.
- Reply text is sent to the script model and to your TTS provider, the same services
  Hermes already uses. Use `script_mode: plain` to avoid the extra model call.
- The plugin stores only the list of chats where you ran `/voicenote off`, under
  `~/.hermes/plugin-data/`. It sends no telemetry.

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check . && pytest
hermes plugins doctor . --ci

# Real end-to-end run: loads the plugin through Hermes in a throwaway
# HERMES_HOME and delivers one voice note to the given chat.
~/.hermes/hermes-agent/venv/bin/python scripts/smoke_e2e.py --chat-id <telegram-chat-id>
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch model and release process.

## License

MIT
