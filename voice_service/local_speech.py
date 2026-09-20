"""Offline speech recognition and synthesis, for testing without a provider.

Vosk for recognition, Piper for synthesis. Both run locally with no API key
and no network, so an inbound call can be taken end to end before any provider
is chosen. Neither is a production choice: the small Vosk model is noticeably
worse than a hosted model on 8 kHz phone audio, and Piper is a turn-based
synthesiser, not a streaming one.

The packages come with `make install`; the models are fetched once with:

    make voice-models

Models are loaded once on first use and reused; loading is measured in seconds
and must not happen per turn.
"""

import io
import json
import logging
import wave
from pathlib import Path

from voice_service.audio import ulaw_to_pcm, wav_to_ulaw

logger = logging.getLogger("voice.local")

# Where make voice-models puts them. Git-ignored: a few hundred MB of binary.
MODEL_DIR = Path("models")
VOSK_MODEL = MODEL_DIR / "vosk-model-small-en-us-0.15"
PIPER_VOICE = MODEL_DIR / "en_US-lessac-medium.onnx"

# The rate the Vosk model was built for. It rejects any other rate rather than
# resampling, so audio is upsampled from the trunk's 8 kHz to match.
VOSK_RATE = 16000

_recognizer_model = None
_piper_voice = None


def _load_vosk():
    global _recognizer_model
    if _recognizer_model is None:
        from vosk import Model, SetLogLevel

        if not VOSK_MODEL.exists():
            raise RuntimeError(f"Vosk model missing at {VOSK_MODEL}. Run: make voice-models")
        SetLogLevel(-1)  # Kaldi is very chatty on stdout otherwise.
        logger.info("loading Vosk model from %s", VOSK_MODEL)
        _recognizer_model = Model(str(VOSK_MODEL))
    return _recognizer_model


def _load_piper():
    global _piper_voice
    if _piper_voice is None:
        from piper import PiperVoice

        if not PIPER_VOICE.exists():
            raise RuntimeError(f"Piper voice missing at {PIPER_VOICE}. Run: make voice-models")
        logger.info("loading Piper voice from %s", PIPER_VOICE)
        _piper_voice = PiperVoice.load(str(PIPER_VOICE))
    return _piper_voice


async def stt(audio: bytes) -> str:
    """Transcribe 8 kHz u-law call audio with Vosk."""
    from vosk import KaldiRecognizer

    recognizer = KaldiRecognizer(_load_vosk(), VOSK_RATE)
    recognizer.AcceptWaveform(ulaw_to_pcm(audio, VOSK_RATE))
    text = json.loads(recognizer.FinalResult()).get("text", "")
    logger.info("stt: %r", text)
    return text


async def tts(text: str) -> bytes:
    """Synthesise `text` with Piper and return it as 8 kHz u-law."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as target:
        _load_piper().synthesize_wav(text, target)
    return wav_to_ulaw(buffer.getvalue())
