"""Translates non-English post text (e.g. Russian) to English. Free Google endpoint via deep-translator."""
import asyncio

from . import config


def _needs(text: str) -> bool:
    return any(c.isalpha() and ord(c) > 127 for c in text)


def _chunks(text, size=4500):
    buf = ""
    for line in text.split("\n"):
        if buf and len(buf) + len(line) + 1 > size:
            yield buf
            buf = ""
        buf += line + "\n"
    if buf:
        yield buf


def _translate(text):
    from deep_translator import GoogleTranslator

    return GoogleTranslator(source="auto", target=config.TRANSLATE_TO).translate(text)


async def translate(text: str) -> str:
    if not config.TRANSLATE_TO or not text or not _needs(text):
        return text
    try:
        parts = [await asyncio.to_thread(_translate, c) for c in _chunks(text)]
        return "\n".join(p.strip() for p in parts if p).strip() or text
    except Exception as ex:
        print("⚠ translation failed, keeping original text:", ex)
        return text
