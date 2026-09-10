"""Audio format conversion between the trunk and the speech models.

The trunk carries 8 kHz mono u-law (`ulaw`), chosen in pjsip.conf so no
transcoding happens during a call. Speech models want linear PCM at their own
rate, so every conversion in the pipeline passes through here.

`audioop` left the standard library in 3.13; the `audioop-lts` backport, a
dependency on those versions, exposes the same API, so this module is
unchanged on either.
"""

import audioop
import io
import wave

# What the trunk delivers and accepts. Anything else needs Asterisk to
# transcode, which is what the codec choice in pjsip.conf exists to avoid.
TELEPHONY_RATE = 8000
SAMPLE_WIDTH = 2  # 16-bit linear, once ulaw is decoded
CHANNELS = 1


def ulaw_to_pcm(ulaw: bytes, rate: int = TELEPHONY_RATE) -> bytes:
    """Decode u-law to 16-bit linear PCM, resampled to `rate`.

    Vosk's models refuse a rate they were not built for -- the small English
    model wants 16 kHz and rejects 8 kHz outright rather than resampling -- so
    upsampling here is required, not an optimisation.
    """
    pcm = audioop.ulaw2lin(ulaw, SAMPLE_WIDTH)
    if rate != TELEPHONY_RATE:
        pcm, _ = audioop.ratecv(pcm, SAMPLE_WIDTH, CHANNELS, TELEPHONY_RATE, rate, None)
    return pcm


def pcm_to_ulaw(pcm: bytes, rate: int) -> bytes:
    """Downsample 16-bit linear PCM to 8 kHz and encode it as u-law."""
    if rate != TELEPHONY_RATE:
        pcm, _ = audioop.ratecv(pcm, SAMPLE_WIDTH, CHANNELS, rate, TELEPHONY_RATE, None)
    return audioop.lin2ulaw(pcm, SAMPLE_WIDTH)


def wav_to_ulaw(data: bytes) -> bytes:
    """Convert a WAV file's bytes to 8 kHz u-law.

    Piper writes WAV at its voice's own rate (22.05 kHz for the medium
    voices), so its output cannot go to the trunk untouched.
    """
    with wave.open(io.BytesIO(data)) as source:
        rate = source.getframerate()
        pcm = source.readframes(source.getnframes())
        if source.getnchannels() != CHANNELS:
            pcm = audioop.tomono(pcm, source.getsampwidth(), 0.5, 0.5)
        if source.getsampwidth() != SAMPLE_WIDTH:
            pcm = audioop.lin2lin(pcm, source.getsampwidth(), SAMPLE_WIDTH)
    return pcm_to_ulaw(pcm, rate)
