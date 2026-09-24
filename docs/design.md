# Design: automatic voice notes

This document consolidates two field reports from building this behavior on two
different Hermes agents for the original author. It records the requirements, the failures that shaped
them, and how this plugin satisfies each one.

## Problem

The user wants every reply in Telegram to be followed by a voice note that
explains the same content in spoken form.

Writing that rule into `SOUL.md`, memory, or a skill did not work. The rule is
text competing with the rest of the context, and the model forgets it. Failures
cluster where the turn ends on a long technical conclusion or right after a
tool call that closes a pending task (commit, PR, DDL). Short conversational
turns rarely fail.

Decision rule from both reports: if an instruction was reinforced once and still
fails, stop adding text. Move the behavior into code. A hook does not compete
with anything.

## Requirements

| # | Requirement | Origin |
|---|---|---|
| 1 | **Deterministic.** Runs from a hook on every reply, not from prompt text. | Both reports |
| 2 | **Text first.** The text reply is never delayed by audio. The voice note always follows it. | Report A |
| 3 | **Real voice note.** Native Telegram voice bubble (Ogg/Opus), never a document or file attachment. | Both reports |
| 4 | **Exactly one** voice note per reply. | Both reports |
| 5 | **Silent operation.** No "audio sent" confirmations or stacked markers in the chat. Report to the user only when a voice note is impossible. | Report A |
| 6 | **Scope.** Only the final reply to the user. Automatic Hermes work (skill/memory review, cron, subagents) is never narrated. | Report A |
| 7 | **Spoken script, not the Markdown.** Tables, lists, and code are explained, not recited. | Both reports |
| 8 | **Inherit the voice.** Use the TTS provider and voice already configured in Hermes. | Report B |
| 9 | **Resilient.** A transient failure does not silently drop the audio. | Report B |
| 10 | **Language follows the user.** The original author works in Spanish; the public default is `language: auto` (same language as the reply). | Report A |

### Resolved contradiction: "synchronous" vs "asynchronous"

Report B asks for the audio "synchronously, after every message". Report A asks
for it "asynchronously, text first". Read in context, they agree:

- Report B's "synchronous" means *always, in the same turn, reliably*.
- Report A's "asynchronous" means *do not make the text wait for the audio*.

The plugin does both: the voice note is scheduled on every reply (guaranteed),
and it is generated after the text is out (non-blocking).

## Architecture

```
turn ends
   │
   ▼
transform_llm_output hook ──► returns None (text is untouched and sent now)
   │
   └─► decide: enabled? user-facing Telegram reply? not a review fork?
               not muted? not a duplicate?
          │ yes
          ▼
       daemon thread (outside the hook timeout)
          ├─ wait start_delay (text lands first)
          ├─ write spoken script  (auxiliary task `voicenote_script`, fallback: cleaned text)
          ├─ synthesize           (Hermes TTS, configured provider and voice)
          ├─ send as voice note   (Telegram sendVoice, retried)
          └─ on final failure: one short text notice
```

| Module | Responsibility |
|---|---|
| `pipeline.py` | Decision rules, background run, retries. No Hermes imports. |
| `script.py` | Spoken-script prompt and deterministic fallback. |
| `guard.py` | Idempotency: sha256 of `target\0text.strip()`, bounded to 64 entries, thread-safe. |
| `delivery.py` | The only module that touches Hermes internals (TTS and Telegram send). |
| `plugin.py` | Registration, session routing, `/voicenote` command. |

### Lessons carried over from the field reports

- **The hook timeout killed finished audio.** Hermes abandons a hook callback
  after `plugins.hook_callback_timeout` (30 s default). One agent generated the
  script inside the hook; when the main model changed to a slower one the script
  took 19 s plus 21 s of TTS, and the finished audio was discarded without any
  visible error. This plugin does all work in its own thread, so the hook
  returns in milliseconds and the timeout no longer applies.
- **The script writer must not inherit a slow main model.** The script is written
  through the plugin's own auxiliary task, `auxiliary.voicenote_script`. Pin a
  fast model there. If the call fails, a deterministic cleanup of the reply is
  spoken instead, so the voice note still arrives.
- **Duplicates.** Earlier versions sent the same audio up to three times. The
  guard makes delivery idempotent per chat and reply text.
- **Background review was narrated.** Hermes runs a skill/memory review fork after
  some turns. Its output is detected through the write origin
  (`tools.skill_provenance.is_background_review`) and skipped.
- **Leftover prompt rules.** Once the plugin owns the behavior, remove any
  voice-note instructions from `SOUL.md`, memory, and skills. Otherwise the model
  also calls `text_to_speech` and the user gets two audios.

## From personal presets to public settings

The first versions encoded the original author's preferences (Spanish scripts,
a specific script model). Before publishing, every preference became a setting
with a neutral default, so any user can decide *when* voice notes are sent
(`chat_types`, `min_response_chars`), *what* is said (`script_mode`, `language`,
`style`, `max_script_words`), and *how* it sounds (`tts_provider`, `tts_speed`,
`tts_instructions`), without touching code. See the README for the full list.

## Known limits

- Interrupted turns do not fire `transform_llm_output`, so they get no voice note.
- `delivery.py` uses internal Hermes functions (`tools.tts_tool.text_to_speech_tool`,
  `tools.send_message_tool._send_to_platform`). A Hermes upgrade can move them;
  that module is intentionally the single place to adapt.
- The voice comes from `tts.*` in Hermes (or `tts_provider` in the plugin
  settings). A voice for another language will sound accented; pick one that
  matches the language you use.
