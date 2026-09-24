# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
