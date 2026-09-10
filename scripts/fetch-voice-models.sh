#!/usr/bin/env bash
# Fetch the offline speech models used for local testing: Vosk for
# recognition, Piper for synthesis. Both land in models/, which is git-ignored
# -- together they are a few hundred MB of binary.
set -euo pipefail

MODEL_DIR="${MODEL_DIR:-models}"
VOSK_MODEL="vosk-model-small-en-us-0.15"
VOSK_URL="https://alphacephei.com/vosk/models/${VOSK_MODEL}.zip"
PIPER_VOICE="${PIPER_VOICE:-en_US-lessac-medium}"

mkdir -p "$MODEL_DIR"

if [ -d "${MODEL_DIR}/${VOSK_MODEL}" ]; then
    echo "Vosk model already present: ${MODEL_DIR}/${VOSK_MODEL}"
else
    echo "Fetching Vosk model ${VOSK_MODEL}..."
    curl -fL --progress-bar -o "${MODEL_DIR}/vosk.zip" "$VOSK_URL"
    unzip -q "${MODEL_DIR}/vosk.zip" -d "$MODEL_DIR"
    rm -f "${MODEL_DIR}/vosk.zip"
fi

if [ -f "${MODEL_DIR}/${PIPER_VOICE}.onnx" ]; then
    echo "Piper voice already present: ${MODEL_DIR}/${PIPER_VOICE}.onnx"
else
    echo "Fetching Piper voice ${PIPER_VOICE}..."
    # Piper's own downloader resolves the voice name and its config together.
    uv run python -m piper.download_voices --data-dir "$MODEL_DIR" "$PIPER_VOICE"
fi

echo
echo "Models ready in ${MODEL_DIR}/:"
du -sh "${MODEL_DIR}"/* 2>/dev/null || true
