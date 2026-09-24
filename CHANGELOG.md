# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
