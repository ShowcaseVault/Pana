# Prompts

Audio played by the dialplan, referenced as `pana/<name>` without an extension
so Asterisk picks the best available format.

Asterisk cannot read mp3: the Ubuntu package ships no `format_mp3`. Convert to
8 kHz mono 16-bit WAV, which is what a ulaw/alaw trunk carries, so no
transcoding happens during the call:

    ffmpeg -i input.mp3 -ar 8000 -ac 1 -acodec pcm_s16le asterisk/sounds/name.wav

Then rebuild the image, since prompts are copied in at build time:

    make asterisk-build && make asterisk-down && make asterisk-up

To check a file is readable by Asterisk before making a call:

    docker exec asterisk-pana asterisk -rx \
        'file convert /usr/share/asterisk/sounds/en/pana/name.wav /tmp/probe.ulaw'

A successful convert prints the duration; the output should be 8000 bytes per
second of audio.

| File | Used by |
|---|---|
| `cid_whistle.wav` | `from-carrier` in `extensions.conf`, the inbound test prompt |
