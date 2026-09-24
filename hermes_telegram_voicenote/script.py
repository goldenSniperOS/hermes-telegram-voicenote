"""Turn a formatted chat reply into a script meant to be heard."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable

logger = logging.getLogger(__name__)

ScriptWriter = Callable[[list[dict[str, str]], float], str]

_SYSTEM_PROMPT = """You write the spoken version of a chat reply. The user will \
listen to it as a voice note, often on the move, instead of reading a long answer \
on a phone screen.

Rules:
- {language_rule}
- Use a warm, natural, conversational tone.
- This is a script to be heard, not read. Never read Markdown, symbols, code, \
URLs, file paths, or table syntax aloud.
- Explain tables, lists, and code in plain words: say what they show and why it \
matters, instead of reciting cells or lines.
- Keep the substance and the conclusion. Drop decoration, repetition, and \
formatting.
- Do not mention that this is audio, a voice note, a script, or a summary.
- Maximum {max_words} words.
- Output only the script text, with no preamble."""

_AUTO_LANGUAGE = "Write in the same language as the reply."

_MEDIA_LINE = re.compile(r"^\s*(MEDIA:\S+|\[\[audio_as_voice\]\]|\[\[as_document\]\])\s*$", re.M)


def strip_delivery_directives(text: str) -> str:
    return _MEDIA_LINE.sub("", text).strip()


def build_messages(
    text: str, *, language: str, max_words: int, style: str = ""
) -> list[dict[str, str]]:
    auto = not language or language.strip().lower() == "auto"
    language_rule = _AUTO_LANGUAGE if auto else f"Write in {language}."
    system = _SYSTEM_PROMPT.format(language_rule=language_rule, max_words=max_words)
    if style:
        system += f"\n\nAdditional style instructions from the user:\n{style}"
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": strip_delivery_directives(text)},
    ]


def fallback_script(text: str, *, max_words: int) -> str:
    """Deterministic cleanup, used for plain mode and when the writer fails."""
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
    style: str = "",
) -> str:
    if writer is not None:
        try:
            messages = build_messages(text, language=language, max_words=max_words, style=style)
            script = (writer(messages, timeout) or "").strip()
            if script:
                return script
            logger.warning("telegram-voicenote: script writer returned empty text; using fallback")
        except Exception as exc:
            logger.warning("telegram-voicenote: script writer failed (%s); using fallback", exc)
    return fallback_script(text, max_words=max_words)
