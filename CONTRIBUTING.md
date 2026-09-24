# Contributing

Thanks for helping improve this plugin. Issues and pull requests are welcome.

## Branch model

| Branch | Purpose |
|---|---|
| `main` | Released code only. Every release tag points to a commit on `main`. |
| `develop` | Integration branch. All feature and fix PRs target `develop`. |
| `feat/<topic>` | New features, branched from `develop`. |
| `fix/<topic>` | Bug fixes, branched from `develop`. |
| `release/vX.Y.Z` | Release preparation, branched from `develop`, merged into `main`. |
| `hotfix/<topic>` | Urgent fixes, branched from `main`, merged into `main` and `develop`. |

## Field-testing loop

This plugin improves from real use on real agents:

1. Install the latest release on an agent and use it normally.
2. When something is off, open a **Field report** issue (or note it and bring
   it back to the maintainer session).
3. Each report becomes a `fix/*` or `feat/*` branch, a PR to `develop`, and a
   regression test that reproduces it.
4. Fixes ship in the next release; agents update with
   `hermes plugins update telegram-voicenote`.

## Workflow

1. Open or pick an issue.
2. Branch from `develop`: `git switch -c feat/my-change develop`.
3. Commit with [Conventional Commits](https://www.conventionalcommits.org/)
   (`feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`).
4. Run the checks locally:
   ```bash
   ruff check . && ruff format --check . && pytest
   hermes plugins doctor . --ci
   ```
5. Open a PR against `develop` and fill in the template. CI must pass. Feature and fix
   PRs are **squash-merged**.

## Release process

1. Branch `release/vX.Y.Z` from `develop`.
2. Bump the version in **three places**: `plugin.yaml`, `pyproject.toml`,
   `hermes_telegram_voicenote/__init__.py`. Tests and the release job fail if they disagree.
3. Move the `[Unreleased]` notes in `CHANGELOG.md` to `## [X.Y.Z] - YYYY-MM-DD`.
4. Open a PR `release/vX.Y.Z` -> `main`. Merge with a **merge commit** (not squash) after
   CI passes, so `main` and `develop` keep a shared history.
5. Tag the merge commit on `main` and push the tag:
   ```bash
   git switch main && git pull
   git tag vX.Y.Z && git push origin vX.Y.Z
   ```
   The `Release` workflow verifies versions and changelog, runs the tests, builds the
   wheel, sdist, and a plugin zip, and publishes a GitHub Release whose notes include
   the exact commit SHA users pin with `--ref`.
6. Merge `main` back into `develop`.

## Community index (optional)

To make the plugin installable by bare name (`hermes plugins install telegram-voicenote`),
submit a PR to the Hermes community plugin index with the entry name, description,
tags, `owner/repo`, and the release commit SHA. Review covers metadata only; it is not
a code audit. The repository must be public.
