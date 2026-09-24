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

Pick one of the two install styles. They update differently.

**Follow the latest version** (simplest):

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --enable
```

**Pin an exact release** (reproducible). Each
[GitHub release](https://github.com/goldenSniperOS/hermes-telegram-voicenote/releases)
lists its commit SHA:

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --ref <commit-sha> --enable
```

Restart the gateway (send `/restart` in Telegram), then send any message.

### Updating

| You installed with | Update with |
|---|---|
| No `--ref` | `hermes plugins update telegram-voicenote` |
| `--ref <sha>` | `hermes plugins install goldenSniperOS/hermes-telegram-voicenote --ref <new-sha> --force --enable` |

`hermes plugins update` refuses pinned installs on purpose, so a pinned agent never
changes version by surprise. Every release note includes the exact command for both
cases. Your settings in `config.yaml` are kept; restart the gateway afterwards.

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

`hermes config set` may print `not a recognized config key` for these two lines. That
warning is harmless: the slot is declared by the plugin when it loads, and the value is
read. Run `/voicenote` after `/restart` to see which model is in use.

Leave the slot unpinned and every script is written by your **main** model. With a large
frontier model that easily adds 5 to 15 seconds per voice note, so the plugin logs a
warning at startup when the slot is unpinned.

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

### 3. Narration rules (`style`)

`style` is appended to the script writer's instructions. It is small in name only: it
is **the** place for your narration policy, and a paragraph of rules works well. A
realistic example for a Spanish voice reading an English-heavy technical agent:

```bash
hermes config set plugins.entries.telegram-voicenote.settings.style "Rioplatense Spanish with voseo. Never read code blocks, commands, file paths, URLs, diffs, or stack traces aloud; say they are in the text. Enumerate lists of up to four items; summarize longer lists in prose. Say numbers and versions as words. Write English technical words the way a Spanish speaker pronounces them: deploy as diploi, cache as cash, commit as comit."
```

Two things the style is for, because the default prompt cannot know them:

- **Regional register.** An `es-AR` voice does not tell the writer to use voseo.
- **Loanword pronunciation.** Non-English TTS voices mangle English technical terms.
  Spelling them phonetically in the script fixes it.

Keep `language` and your TTS voice in the same language. A Spanish script through an
`en-US` voice sounds wrong and nothing warns you.

### 4. All settings

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
| `style` | *(empty)* | Narration rules appended to the writer's prompt. See [Narration rules](#3-narration-rules-style). |
| `script_timeout` | `90` | Seconds allowed for the script model before falling back to plain mode. |
| **How it sounds** | | |
| `tts_provider` | *(global)* | TTS provider for voice notes only, for example `openai`, `elevenlabs`, `edge`. |
| `tts_speed` | *(global)* | Playback speed from `0.25` to `4.0`. |
| `tts_instructions` | *(empty)* | Voice direction for providers that support it. |
| **Reliability** | | |
| `retries` | `2` | Extra attempts when synthesis or delivery fails. |
| `notify_on_failure` | `true` | Send one short message only when a voice note is impossible. |
| `failure_message` | *(English)* | Text of that message. `{reason}` is replaced with the error type. It does not follow `language`; translate it yourself. |
| **API keys** | | |
| `setkey_enabled` | `false` | Allow `/setkey` in a private chat (see [Setting a key from your phone](#setting-a-key-from-your-phone-setkey)). |
| `setkey_allowed` | *(TTS + OpenRouter keys)* | Credential names `/setkey` may write. |

### Per chat

```
/voicenote        show the version, script model, and every effective setting
/voicenote off    stop voice notes in this chat
/voicenote on     resume them
/setkey NAME key  store an API key (private chat, off by default)
```

## Troubleshooting

| Symptom | Check |
|---|---|
| No voice note at all | `hermes plugins list` shows `enabled`; you ran `/restart`; `/voicenote` says `on`. |
| No voice note from a script or terminal command | By design. Voice notes are sent only from the running gateway, never from a CLI session or a subprocess that inherited chat variables. |
| Two voice notes per reply | Another plugin or `/voice tts` also speaks replies. Check `hermes plugins list` and the leftovers described in [Migrating from another plugin](#migrating-from-another-plugin). |
| A long voice note arrives as several bubbles | Hermes splits long scripts; every part is sent in order. Lower `max_script_words` for one bubble. |
| Voice note arrives as a file | Install `ffmpeg` so audio can be converted to Opus. |
| Two audios per reply | Run `/voice off`, and remove voice rules from `SOUL.md` or memory. |
| Voice notes are slow | Pin a fast model in `auxiliary.voicenote_script`, or use `script_mode: plain`. |
| Wrong accent | Pick a TTS voice for your language (`tts.edge.voice`, or `tts_provider`). |
| Failure notice after switching TTS provider | The provider's API key is missing or wrong. See [API keys for TTS providers](#api-keys-for-tts-providers). |

Logs:

```bash
grep telegram-voicenote ~/.hermes/logs/gateway.log | tail -20
```

Still stuck, or it misbehaved on a real agent? Open a
[Field report](https://github.com/goldenSniperOS/hermes-telegram-voicenote/issues/new/choose).

## Security and privacy

### API keys for TTS providers

API keys belong to **Hermes**, not to this plugin. The plugin uses whatever TTS
provider and script model Hermes is configured with, so the key must be set the
way Hermes expects it. Each provider reads its key from an environment variable:

| TTS provider (`tts.provider` or `tts_provider`) | Variable |
|---|---|
| `edge` (default) | none, it is free |
| `openai` | `VOICE_TOOLS_OPENAI_KEY`, falling back to `OPENAI_API_KEY` |
| `elevenlabs` | `ELEVENLABS_API_KEY` |
| `mistral` | `MISTRAL_API_KEY` |
| `gemini` | `GEMINI_API_KEY` or `GOOGLE_API_KEY` |
| `minimax` | `MINIMAX_API_KEY` |
| `deepinfra` | `DEEPINFRA_API_KEY` |

The script model (`auxiliary.voicenote_script`) uses the key of whichever provider
you picked, for example `OPENROUTER_API_KEY`.

If the key is missing or wrong, TTS fails, the plugin retries, and you get one short
failure notice instead of a voice note. Check the gateway log for the provider's
error.

### Setting a key from your phone: `/setkey`

**Never paste a key into a normal chat message.** Telegram has no hidden input
field, and Hermes has no secure secret entry over messaging platforms. A key sent
as a normal message ends up in the Telegram history, the session transcript, and
the gateway log.

For the common case (you are on your phone and cannot reach a terminal), the
plugin adds a `/setkey` command. It is **off by default**. Enable it once on the
Hermes machine:

```bash
hermes config set plugins.entries.telegram-voicenote.settings.setkey_enabled true
```

Restart the gateway. Then, in a **private chat** with your bot:

```
/setkey ELEVENLABS_API_KEY sk_your_key_here
```

What happens:

1. The command is intercepted **before it reaches Hermes**. It never becomes an
   agent turn, never enters the session transcript, and never reaches the gateway
   log (the plugin logs only the variable name).
2. The key is saved to `~/.hermes/.env` through Hermes' own credential routine,
   the same one the Desktop app and `hermes auth` use.
3. Your message is **deleted** from the chat, and the bot replies with a masked
   confirmation such as `Saved ELEVENLABS_API_KEY (...here)`.
4. Send `/restart` so every provider picks up the new key.

Safeguards:

- Private chats only. In a group the message is deleted and refused.
- Only users Hermes already authorizes (`TELEGRAM_ALLOWED_USERS` and friends).
  Anyone else is refused, fail-closed.
- Only names in an allowlist. By default: `VOICE_TOOLS_OPENAI_KEY`,
  `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, `MISTRAL_API_KEY`, `GEMINI_API_KEY`,
  `GOOGLE_API_KEY`, `MINIMAX_API_KEY`, `DEEPINFRA_API_KEY`, `OPENROUTER_API_KEY`.
  Change it with `setkey_allowed`.
- Names that control access to the bot itself (`TELEGRAM_BOT_TOKEN`,
  `TELEGRAM_ALLOWED_USERS`, `GATEWAY_ALLOW_ALL_USERS`, `SUDO_PASSWORD`) can never be
  written from the chat, even if you add them to the allowlist.

What it cannot protect:

- **Telegram itself saw the message.** Bot chats are not end-to-end encrypted, so
  the key passed through Telegram's servers before it was deleted. Treat `/setkey`
  as "safe enough for a personal API key with a spending limit", not as a vault.
  Rotate a key if you are unsure.
- If the bot cannot delete the message (it usually can in a private chat), the
  reply tells you to delete it yourself.

### Setting a key on the Hermes machine

When you do have access to the machine, these are preferable:

- Edit `~/.hermes/.env` (owner-only permissions) and add `ELEVENLABS_API_KEY=...`.
- Run `hermes auth add <provider>`, which prompts for the key without echoing it.
- Use a password manager through Hermes'
  [secret sources](https://hermes-agent.nousresearch.com/docs/user-guide/secrets)
  (Bitwarden, 1Password, or any CLI).

`hermes config set OPENAI_API_KEY <value>` also writes to `.env`, but the value
stays in your shell history.

### What the plugin does with your data

- Plugins run inside Hermes with its permissions. Review the code before enabling it.
- Reply text is sent to the script model and to your TTS provider, the same services
  Hermes already uses. Use `script_mode: plain` to avoid the extra model call.
- The plugin stores only the list of chats where you ran `/voicenote off`, under
  `~/.hermes/plugin-data/`. It sends no telemetry.
- `/setkey` writes only to Hermes' `.env`, never to the plugin's own data, and never
  logs the value.

## Migrating from another plugin

`hermes plugins remove <old-plugin>` deletes the directory but leaves its entries in
`config.yaml` (`plugins.enabled`, `plugins.entries.<old-plugin>`). Clean them up:

```bash
hermes config set plugins.enabled '["telegram-voicenote"]'   # keep your other plugins in the list
hermes config unset plugins.entries.<old-plugin>
```

Then remove any old instruction that told the agent to send audio itself (in
`SOUL.md`, memories, or skills), turn off `/voice tts`, and `/restart`.

## Development

On Windows with git-bash, pass the plugin id to `doctor` instead of a `~/...` path; MSYS
paths are not recognized.

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
ruff check . && pytest
hermes plugins doctor . --ci            # or: hermes plugins doctor telegram-voicenote --ci

# Real end-to-end run: loads the plugin through Hermes in a throwaway
# HERMES_HOME and delivers one voice note to the given chat.
~/.hermes/hermes-agent/venv/bin/python scripts/smoke_e2e.py --chat-id <telegram-chat-id>
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branch model and release process.

## License

MIT
