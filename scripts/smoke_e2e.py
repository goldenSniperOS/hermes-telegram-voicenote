"""End-to-end smoke test against a real Hermes install.

Loads the plugin through Hermes' own PluginManager inside a throwaway
HERMES_HOME, fires the ``transform_llm_output`` hook exactly as the agent loop
does, and waits for the voice note to be delivered to a real Telegram chat.

Nothing is installed into the user's Hermes. Secrets and TTS settings are read
from the real Hermes home and copied into the temporary one.

Usage (run with the Hermes interpreter):

    ~/.hermes/hermes-agent/venv/bin/python scripts/smoke_e2e.py --chat-id <id>
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
import threading
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SAMPLE = """## Release status

| Step | Result |
|---|---|
| CI | passed |
| Release | published |

Version **0.2.0** is out and installs cleanly from GitHub."""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat-id", required=True)
    parser.add_argument("--timeout", type=float, default=120)
    args = parser.parse_args()

    real_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
    temp_home = Path(tempfile.mkdtemp(prefix="voicenote-smoke-"))
    try:
        for name in (".env", "config.yaml"):
            if (real_home / name).exists():
                shutil.copy2(real_home / name, temp_home / name)
        plugin_dir = temp_home / "plugins" / "telegram-voicenote"
        shutil.copytree(
            REPO,
            plugin_dir,
            ignore=shutil.ignore_patterns(
                ".git", ".venv", "__pycache__", "dist", "build", ".engram"
            ),
        )
        os.environ["HERMES_HOME"] = str(temp_home)
        os.environ["HERMES_ENABLE_PROJECT_PLUGINS"] = "0"

        from hermes_cli.env_loader import load_hermes_dotenv

        load_hermes_dotenv()

        # Count real deliveries from the plugin's own log line: this is exactly
        # what the user would see in the chat, independent of thread timing.
        deliveries: list[str] = []

        class _DeliveryCounter(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                if "telegram-voicenote: delivered to" in record.getMessage():
                    deliveries.append(record.getMessage())

        logging.getLogger().addHandler(_DeliveryCounter())
        logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
        logging.getLogger("hermes_telegram_voicenote").setLevel(logging.INFO)
        for name in list(logging.root.manager.loggerDict):
            if "voicenote" in name:
                logging.getLogger(name).setLevel(logging.INFO)

        from hermes_cli.plugins import get_plugin_manager

        # Use the process-global manager: ctx.llm checks auxiliary-task ownership
        # against it, exactly as in the running gateway.
        manager = get_plugin_manager()
        manager.discover_and_load()
        loaded = manager._plugins.get("telegram-voicenote")
        if loaded is None or not loaded.enabled:
            # Not enabled in the copied config: load it explicitly, exactly once.
            manifests = manager._scan_directory(temp_home / "plugins", source="user")
            manager._load_plugin(manifests[0])
            loaded = manager._plugins["telegram-voicenote"]
        assert not loaded.error, loaded.error
        registered = manager._hooks.get("transform_llm_output", [])
        ours = [cb for cb in registered if "VoiceNotePipeline" in getattr(cb, "__qualname__", "")]
        print(f"loaded: hooks={list(loaded.hooks_registered)} registrations={len(ours)}")

        from gateway.session_context import set_session_vars

        set_session_vars(platform="telegram", chat_id=args.chat_id)

        before = {t.ident for t in threading.enumerate()}
        started = time.monotonic()
        results = manager.invoke_hook(
            "transform_llm_output",
            response_text=SAMPLE,
            session_id="smoke",
            model="smoke",
            platform="telegram",
        )
        hook_ms = (time.monotonic() - started) * 1000
        print(f"hook returned {results!r} in {hook_ms:.0f} ms")
        assert all(r is None for r in results), "hook must never replace the reply"

        workers = [
            t
            for t in threading.enumerate()
            if t.ident not in before and t.name == "telegram-voicenote"
        ]
        assert workers, "no background worker was started"
        workers[0].join(args.timeout)
        if workers[0].is_alive():
            print("FAIL: worker still running after timeout")
            return 1
        print(f"worker finished in {time.monotonic() - started:.1f}s")

        # A duplicate of the same reply must not produce a second voice note.
        manager.invoke_hook(
            "transform_llm_output",
            response_text=SAMPLE,
            session_id="smoke",
            model="smoke",
            platform="telegram",
        )
        # Give any (wrongly) scheduled second worker time to deliver.
        time.sleep(min(args.timeout, 30))
        print(f"deliveries: {len(deliveries)}")
        ok = len(deliveries) == 1
        print("dedup:", "OK" if ok else f"FAIL ({len(deliveries)} voice notes delivered)")
        return 0 if ok else 1
    finally:
        shutil.rmtree(temp_home, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
