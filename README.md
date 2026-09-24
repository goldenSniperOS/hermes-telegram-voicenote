# hermes-telegram-voicenote

A [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin that attaches an
extra Telegram voice note to the agent's responses, using the TTS provider already
configured in Hermes.

> Status: **scaffold (v0.1.0)**. The plugin installs and registers a `/voicenote`
> status command. Voice note generation is in progress — see the issues.

## Install

Hermes plugins install from Git:

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --enable
```

Pin an exact release commit (recommended for reproducible installs):

```bash
hermes plugins install goldenSniperOS/hermes-telegram-voicenote --ref <40-char-commit-sha> --enable
```

Each GitHub release lists its commit SHA. Alternatively, install the wheel attached to a
release into the Python environment Hermes runs in:

```bash
pip install hermes_telegram_voicenote-<version>-py3-none-any.whl
```

Then restart the gateway (send `/restart` from Telegram).

Manage it:

```bash
hermes plugins list
hermes plugins update telegram-voicenote
hermes plugins disable telegram-voicenote
hermes plugins remove telegram-voicenote
```

## Usage

In any Hermes chat:

```
/voicenote
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
