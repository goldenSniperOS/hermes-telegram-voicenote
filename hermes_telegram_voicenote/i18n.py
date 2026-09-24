"""Small language helpers: default failure notice and voice/language checks."""

from __future__ import annotations

# language name (lower case) -> (ISO 639-1 code, default failure notice)
LANGUAGES: dict[str, tuple[str, str]] = {
    "english": ("en", "I could not generate the voice note for this reply ({reason})."),
    "spanish": ("es", "No pude generar la nota de voz de esta respuesta ({reason})."),
    "español": ("es", "No pude generar la nota de voz de esta respuesta ({reason})."),
    "portuguese": ("pt", "Não consegui gerar a mensagem de voz desta resposta ({reason})."),
    "português": ("pt", "Não consegui gerar a mensagem de voz desta resposta ({reason})."),
    "french": ("fr", "Je n'ai pas pu générer la note vocale de cette réponse ({reason})."),
    "français": ("fr", "Je n'ai pas pu générer la note vocale de cette réponse ({reason})."),
    "german": ("de", "Ich konnte die Sprachnachricht für diese Antwort nicht erzeugen ({reason})."),
    "deutsch": (
        "de",
        "Ich konnte die Sprachnachricht für diese Antwort nicht erzeugen ({reason}).",
    ),
    "italian": (
        "it",
        "Non sono riuscito a generare il messaggio vocale di questa risposta ({reason}).",
    ),
    "italiano": (
        "it",
        "Non sono riuscito a generare il messaggio vocale di questa risposta ({reason}).",
    ),
}


def language_code(language: str) -> str:
    """ISO code for a language name or code; empty when unknown or ``auto``."""
    value = (language or "").strip().lower()
    if value in LANGUAGES:
        return LANGUAGES[value][0]
    if len(value) == 2 and value.isalpha():
        return value
    base = value.split("-")[0].split("_")[0]
    return base if len(base) == 2 and base.isalpha() and value != "auto" else ""


def default_failure_message(language: str) -> str:
    entry = LANGUAGES.get((language or "").strip().lower())
    return entry[1] if entry else LANGUAGES["english"][1]


def voice_language(tts_config: dict, provider: str) -> str:
    """Language code implied by the configured voice, e.g. es-MX-DaliaNeural -> es."""
    section = (tts_config or {}).get(provider) or {}
    voice = str(section.get("voice") or "")
    prefix = voice.split("-")[0].lower()
    if len(prefix) == 2 and prefix.isalpha() and "-" in voice:
        return prefix
    return ""


def mismatch(language: str, tts_config: dict, provider: str = "") -> str:
    """A warning when the script language and the voice language differ, else ''."""
    provider = provider or str((tts_config or {}).get("provider") or "edge")
    want, have = language_code(language), voice_language(tts_config, provider)
    if want and have and want != have:
        return (
            f"telegram-voicenote: language is {language!r} but the {provider} voice is "
            f"{have!r}; the voice note will sound wrong. Set tts.{provider}.voice to a "
            f"{want!r} voice or change language."
        )
    return ""
