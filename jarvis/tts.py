"""Synthèse vocale (texte -> MP3).

ElevenLabs si une clé est configurée, sinon edge-tts (gratuit).
"""

from __future__ import annotations

import asyncio

import requests

from . import config, voices

ELEVEN_API = "https://api.elevenlabs.io/v1"


# Voix masculines posées pour parler d'autres langues (traducteur) avec la voix gratuite.
LANGUAGE_VOICES = {
    "en": "en-GB-RyanNeural", "es": "es-ES-AlvaroNeural", "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural", "pt": "pt-BR-AntonioNeural", "nl": "nl-NL-MaartenNeural",
    "ar": "ar-SA-HamedNeural", "ja": "ja-JP-KeitaNeural", "zh": "zh-CN-YunxiNeural",
    "ru": "ru-RU-DmitryNeural", "pl": "pl-PL-MarekNeural", "tr": "tr-TR-AhmetNeural",
    "ko": "ko-KR-InJoonNeural", "hi": "hi-IN-MadhurNeural", "sv": "sv-SE-MattiasNeural",
}


def synthesize(text: str, voice: str | None = None, lang: str | None = None) -> bytes:
    """Renvoie le MP3 de `text` lu avec la voix choisie (prénom ou identifiant).
    `lang` (ex. « en ») : faire parler Jarvis dans une autre langue."""
    lang = (lang or "fr").lower()[:2]
    provider, voice_id = voices.resolve(voice or voices.load_saved_voice())
    if provider == "elevenlabs":
        try:
            return _eleven_tts(text, voice_id, lang)
        except Exception as exc:  # quota épuisé, réseau… : on continue avec la voix gratuite
            print(f"[voix] ElevenLabs indisponible ({exc}), voix gratuite utilisée.")
            voice_id = voices.EDGE_VOICES["Henri"][0]
    if lang != "fr":
        voice_id = LANGUAGE_VOICES.get(lang, "en-GB-RyanNeural")
    return _edge_tts(text, voice_id)


def _eleven_tts(text: str, voice_id: str, lang: str = "fr") -> bytes:
    response = requests.post(
        f"{ELEVEN_API}/text-to-speech/{voice_id}",
        params={"output_format": "mp3_44100_128"},
        headers={"xi-api-key": config.get("elevenlabs_cle") or ""},
        json={
            "text": text,
            "model_id": config.get("elevenlabs_modele", "eleven_multilingual_v2"),
            "language_code": lang,
            # ElevenLabs accepte une vitesse de 0,7 à 1,2 (pas de réglage de hauteur).
            "voice_settings": {"speed": max(0.7, min(1.2, 1 + int(voices.rate()[:-1]) / 100))},
        },
        timeout=60,
    )
    if response.status_code == 400 and "language_code" in response.text:
        # Certains modèles n'acceptent pas language_code : on réessaie sans.
        response = requests.post(
            f"{ELEVEN_API}/text-to-speech/{voice_id}",
            params={"output_format": "mp3_44100_128"},
            headers={"xi-api-key": config.get("elevenlabs_cle") or ""},
            json={"text": text, "model_id": config.get("elevenlabs_modele", "eleven_multilingual_v2")},
            timeout=60,
        )
    response.raise_for_status()
    return response.content


def _edge_tts(text: str, voice_id: str) -> bytes:
    import edge_tts

    async def run() -> bytes:
        audio = bytearray()
        speech = edge_tts.Communicate(text, voice_id, rate=voices.rate(), pitch=voices.pitch())
        async for chunk in speech.stream():
            if chunk["type"] == "audio":
                audio.extend(chunk["data"])
        return bytes(audio)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run())
    # Appelé depuis une boucle asyncio (interface) : on passe par un thread.
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(1) as pool:
        return pool.submit(asyncio.run, run()).result()

