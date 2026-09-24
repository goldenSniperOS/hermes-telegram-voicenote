"""Turn a formatted chat reply into a script meant to be heard."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

logger = logging.getLogger(__name__)

ScriptWriter = Callable[[list[dict[str, str]], float], str]

_SYSTEM_PROMPT = """You write the spoken version of a chat reply that the user will \
listen to as a voice note.

Rules:
- Write in {language}, in a warm, natural, conversational tone.
- This is a script to be heard, not read. Never read Markdown, symbols, code, \
URLs, file paths, or table syntax aloud.
- Explain tables, lists, and code in plain words: say what they show and why it \
matters, instead of reciting cells or lines.
- Keep the substance and the conclusion. Drop decoration, repetition, and \
formatting.
- Do not mention that this is audio, a voice note, a script, or a summary.
- Maximum {max_words} words.
- Output only the script text, with no preamble."""

_MEDIA_LINE = re.compile(r"^\s*(MEDIA:\S+|\[\[audio_as_voice\]\]|\[\[as_document\]\])\s*$", re.M)


def strip_delivery_directives(text: str) -> str:
    return _MEDIA_LINE.sub("", text).strip()


def build_messages(text: str, *, language: str, max_words: int) -> list[dict[str, str]]:
    system = _SYSTEM_PROMPT.format(language=language, max_words=max_words)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": strip_delivery_directives(text)},
    ]


def fallback_script(text: str, *, max_words: int) -> str:
    """Deterministic cleanup used when the script writer is unavailable."""
    cleaned = strip_delivery_directives(text)
    try:
        from tools.tts_text_normalize import prepare_spoken_text

        cleaned = prepare_spoken_text(cleaned, max_chars=None)
    except Exception:
        cleaned = re.sub(r"```.*?```", " ", cleaned, flags=re.S)
        cleaned = re.sub(r"[`*_#>|\[\]]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
    words = cleaned.split()
    return " ".join(words[:max_words])


def make_script(
    text: str,
    writer: ScriptWriter | None,
    *,
    language: str,
    max_words: int,
    timeout: float,
) -> str:
    if writer is not None:
        try:
            script = (
                writer(build_messages(text, language=language, max_words=max_words), timeout) or ""
            ).strip()
            if script:
                return script
            logger.warning("telegram-voicenote: script writer returned empty text; using fallback")
        except Exception as exc:
            logger.warning("telegram-voicenote: script writer failed (%s); using fallback", exc)
    return fallback_script(text, max_words=max_words)
