# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.5.2] - 2026-09-23

### Fixed
- `scripts/smoke_e2e.py` always counted 0 deliveries: Hermes imports plugins under
  a namespaced package, so the log levels set before discovery never applied. The
  smoke now counts successful sends at `tools.send_message_tool._send_to_platform`,
  the boundary every pipeline instance goes through, and raises plugin log levels
  after discovery.
- If a Hermes upgrade removes `gateway.run._gateway_runner_ref` or
  `GatewayRunner._gateway_loop`, the plugin now logs one clear error instead of
  silently disabling voice notes.

### Changed
- The default `failure_message` follows `language` (English, Spanish, Portuguese,
  French, German, Italian). A custom `failure_message` still wins.
- Warning at startup, and in `/voicenote`, when a pinned `language` does not match
  the language of the configured TTS voice.

## [0.5.1] - 2026-09-23

Fixes from three field reports.

### Fixed
- **Voice notes could be sent from non-chat processes.** A CLI run or a
  subprocess (terminal tool, script) that inherited `HERMES_SESSION_*` from a chat
  turn looked like a live chat and delivered audio. The plugin now delivers only
  when this process runs the gateway.
- **Long replies lost audio after the first part.** Hermes splits long TTS text
  and returns `file_paths`; only `file_path` was sent. Every part is now sent in
  order, and a retry resumes after the last part that was delivered.
- Delivery no longer calls `load_gateway_config()` per voice note (which re-entered
  plugin discovery); it uses the running gateway's config.
- `scripts/smoke_e2e.py` now fails if the plugin is registered more than once after
  the first delivery (lazy discovery from the script-model call).

### Changed
- `/voicenote` shows the script model and every effective setting.
- Startup warning when `auxiliary.voicenote_script` is unpinned.

### Documentation
- `style` is documented as the place for narration rules, with a full example
  (register, what not to read aloud, loanword phonetics).
- `failure_message` does not follow `language`.
- The `not a recognized config key` warning for `auxiliary.voicenote_script` is harmless.
- Migrating from another plugin: cleaning up the leftover config entries.
- Windows: pass the plugin id to `hermes plugins doctor`.

## [0.5.0] - 2026-09-23

### Added
- `/setkey NAME value`: store an API key from a private Telegram chat without it
  reaching Hermes. The command is handled by a native Telegram handler that runs
  before the gateway, so the message never becomes an agent turn, never enters the
  transcript, and never reaches the gateway log. The key is saved through Hermes'
  own credential routine and the message is deleted. Off by default
  (`setkey_enabled`), private chats and authorized users only, allowlisted names
  only (`setkey_allowed`), and bot-access variables are never writable.

### Documentation
- README: API keys belong to Hermes; table of the variable each TTS provider
  reads; how to set a key from the phone and from the Hermes machine; honest limits
  (Telegram still saw the message).

## [0.4.3] - 2026-09-23

### Documentation
- README: how to add API keys for TTS providers and the script model without
  pasting them into the chat (Telegram has no hidden input and Hermes does not
  support secure secret entry over messaging), using `~/.hermes/.env` or a secret
  source, plus which environment variables each TTS provider reads.

## [0.4.2] - 2026-09-23

### Fixed
- Documented updates: `hermes plugins update` refuses installs pinned with `--ref`
  (verified on Hermes v0.21.0), which is the install style the README recommended.
  The README now has an "Updating" section, and every release note includes the
  exact update command for pinned and unpinned installs.

### Documentation
- CONTRIBUTING: every failure found in use ships as a new patch version.

## [0.4.1] - 2026-09-23

### Fixed
- If the plugin is registered twice in one process (for example after a plugin
  reload), a reply was voiced twice. The idempotency guard is now shared by every
  registration in the process.

### Changed
- `scripts/smoke_e2e.py` now lets Hermes discover the plugin like the gateway does,
  and counts real deliveries instead of live threads.

## [0.4.0] - 2026-09-23

First public release.

### Added
- Settings for every user, with neutral defaults: `chat_types`, `script_mode`
  (`llm` or `plain`), `style`, `tts_provider`, `tts_speed`, `tts_instructions`,
  and `failure_message`.
- `/voicenote` now shows the effective settings.

### Changed
- `language` defaults to `auto` (the language of the reply) instead of Spanish.
- The failure notice is configurable.

### Documentation
- README rewritten for public use: the problem it solves (listening on the go),
  why the alternatives fall short, a setup checklist, a full configuration
  reference, troubleshooting, and security notes.
- CODE_OF_CONDUCT added.

## [0.3.0] - 2026-09-23

First release intended for field use on real agents.

### Added
- `scripts/smoke_e2e.py`: loads the plugin through Hermes' own plugin manager in a
  throwaway `HERMES_HOME` and delivers one real voice note, including a dedup check.
- "Field report" issue form and a field-testing loop in CONTRIBUTING.

### Documentation
- README: why the built-in `/voice tts` mode is not enough, a new-agent checklist,
  and the latency cost of not pinning `auxiliary.voicenote_script`.

## [0.2.0] - 2026-09-23

### Added
- Automatic voice note after every Telegram reply via the `transform_llm_output` hook.
- Spoken-script writer on the plugin-owned auxiliary task `voicenote_script`, with a
  deterministic fallback when the model call fails.
- Background delivery thread: text is never delayed and the hook timeout cannot drop audio.
- Idempotency guard (one voice note per chat and reply), retries, and a single failure notice.
- Skips background skill/memory review, cron, and non-Telegram sessions.
- `/voicenote on|off` per-chat toggle and plugin settings under `plugins.entries`.
- `docs/design.md` consolidating the requirements and field lessons.

## [0.1.1] - 2026-09-23

### Fixed
- Use `manifest_version: 1` so `hermes plugins install` accepts the plugin.

## [0.1.0] - 2026-09-23

### Added
- Plugin scaffold: `plugin.yaml`, `register(ctx)` entry point, `/voicenote` status command.
- CI (lint, tests, build) and tag-driven release workflow.
