# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed
- Use `manifest_version: 1` so `hermes plugins install` accepts the plugin.

## [0.1.0] - 2026-09-23

### Added
- Plugin scaffold: `plugin.yaml`, `register(ctx)` entry point, `/voicenote` status command.
- CI (lint, tests, build) and tag-driven release workflow.
