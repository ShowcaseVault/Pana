"""Smoke test for the NVIDIA-hosted Magpie TTS endpoint.

Streams speech from NVIDIA Cloud Functions and plays it live through aplay as
chunks arrive. No GPU and no local container required -- the model runs on
NVIDIA's hardware.

    uv add nvidia-riva-client
    uv run python scripts/test_magpie_tts.py --text "Hello from Pana."

The function ID and voice names below are defaults. Confirm the current values
on https://build.nvidia.com/nvidia/magpie-tts-multilingual/api and override with
--function-id / --voice if the call fails with NOT_FOUND or an invalid voice.
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
import time
import wave
from pathlib import Path

sys.path.insert(0,"/home/vishal/Project/Pana")

from api.config.config import settings

NVCF_URI = "grpc.nvcf.nvidia.com:443"
DEFAULT_FUNCTION_ID = "877104f7-e885-42b9-8de8-f6e4c6303969"
DEFAULT_VOICE = "Magpie-Multilingual.EN-US.Sofia"
DEFAULT_LANGUAGE = "en-US"
SAMPLE_RATE_HZ = 44100
SAMPLE_WIDTH_BYTES = 2  # LINEAR_PCM is 16-bit


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--text", default="Hello from Pana. This is a text to speech test.")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE)
    parser.add_argument("--function-id", default=DEFAULT_FUNCTION_ID)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("magpie_test.wav"),
        help="WAV file to also write the full audio to",
    )
    parser.add_argument(
        "--no-play",
        action="store_true",
        help="synthesize and save without playing audio",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="use synthesize() instead of streaming; play only once complete",
    )
    return parser.parse_args()


def build_service(function_id: str):
    import riva.client

    api_key = settings.NVIDIA_API_KEY
    if not api_key:
        sys.exit("NVIDIA_API_KEY is empty. Set it in .env before running.")

    auth = riva.client.Auth(
        uri=NVCF_URI,
        use_ssl=True,
        metadata_args=[
            ["function-id", function_id],
            ["authorization", f"Bearer {api_key}"],
        ],
    )
    return riva.client.SpeechSynthesisService(auth)


def start_player() -> subprocess.Popen | None:
    """Spawn aplay reading raw PCM from stdin, so chunks play as they arrive."""
    if shutil.which("aplay") is None:
        print("aplay not found; skipping playback (audio is still written to --output)")
        return None

    return subprocess.Popen(
        [
            "aplay",
            "-q",
            "-f",
            "S16_LE",
            "-r",
            str(SAMPLE_RATE_HZ),
            "-c",
            "1",
            "-",
        ],
        stdin=subprocess.PIPE,
    )


def write_wav(path: Path, audio: bytes) -> None:
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(SAMPLE_WIDTH_BYTES)
        handle.setframerate(SAMPLE_RATE_HZ)
        handle.writeframes(audio)


def main() -> None:
    import riva.client

    args = parse_args()
    service = build_service(args.function_id)

    request = {
        "text": args.text,
        "voice_name": args.voice,
        "language_code": args.language,
        "sample_rate_hz": SAMPLE_RATE_HZ,
        "encoding": riva.client.AudioEncoding.LINEAR_PCM,
    }

    print(f"voice: {args.voice}  ({args.language})")
    print(f"text:  {args.text}\n")

    player = None if args.no_play else start_player()
    chunks: list[bytes] = []
    first_chunk_at: float | None = None
    started = time.perf_counter()

    try:
        if args.batch:
            audio = service.synthesize(**request).audio
            first_chunk_at = time.perf_counter() - started
            chunks.append(audio)
            if player is not None:
                player.stdin.write(audio)
        else:
            for response in service.synthesize_online(**request):
                if not response.audio:
                    continue
                if first_chunk_at is None:
                    first_chunk_at = time.perf_counter() - started
                chunks.append(response.audio)
                if player is not None:
                    # write straight through so playback starts before
                    # synthesis finishes
                    player.stdin.write(response.audio)
                    player.stdin.flush()
    except BrokenPipeError:
        print("playback pipe closed early; audio still captured")
    finally:
        if player is not None and player.stdin is not None:
            with contextlib.suppress(BrokenPipeError):
                player.stdin.close()

    elapsed = time.perf_counter() - started
    audio = b"".join(chunks)

    if player is not None:
        player.wait()

    if not audio:
        sys.exit("no audio returned; check --function-id and --voice")

    duration = len(audio) / (SAMPLE_RATE_HZ * SAMPLE_WIDTH_BYTES)
    write_wav(args.output, audio)

    print(f"chunks:          {len(chunks)}")
    if first_chunk_at is not None:
        print(f"time to first:   {first_chunk_at:.3f}s")
    print(f"synthesis time:  {elapsed:.3f}s")
    print(f"audio duration:  {duration:.2f}s")
    print(f"bytes:           {len(audio)}")
    print(f"wrote:           {args.output.resolve()}")


if __name__ == "__main__":
    main()
