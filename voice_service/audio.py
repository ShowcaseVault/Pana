"""Audio format conversion between the trunk and the speech models.

The trunk carries 8 kHz mono u-law (`ulaw`), chosen in pjsip.conf so no
transcoding happens during a call. Speech models want linear PCM at their own
rate, so every conversion in the pipeline passes through here.

`audioop` left the standard library in 3.13; the `audioop-lts` backport, a
dependency on those versions, exposes the same API, so this module is
unchanged on either.
"""

import audioop

# What the trunk delivers and accepts. Anything else needs Asterisk to
# transcode, which is what the codec choice in pjsip.conf exists to avoid.
TELEPHONY_RATE = 8000
SAMPLE_WIDTH = 2  # 16-bit linear, once ulaw is decoded
CHANNELS = 1


def ulaw_to_pcm(ulaw: bytes, rate: int = TELEPHONY_RATE) -> bytes:
    """Decode u-law to 16-bit linear PCM, resampled to `rate`."""
    pcm = audioop.ulaw2lin(ulaw, SAMPLE_WIDTH)
    if rate != TELEPHONY_RATE:
        pcm, _ = audioop.ratecv(pcm, SAMPLE_WIDTH, CHANNELS, TELEPHONY_RATE, rate, None)
    return pcm


def pcm_to_ulaw(pcm: bytes, rate: int, state: object = None) -> tuple[bytes, object]:
    """Downsample 16-bit linear PCM to 8 kHz and encode it as u-law.

    Returns the audio and the resampler's state. A stream arriving in chunks
    must pass that state back on the next call: the conversion ratio is rarely
    a whole number of samples (22.05 kHz to 8 kHz is 2.75625), so a chunk
    resampled from a standing start loses the fraction at its edge, and every
    boundary clicks. Callers converting one whole buffer can ignore it.
    """
    if rate != TELEPHONY_RATE:
        pcm, state = audioop.ratecv(pcm, SAMPLE_WIDTH, CHANNELS, rate, TELEPHONY_RATE, state)
    return audioop.lin2ulaw(pcm, SAMPLE_WIDTH), state
