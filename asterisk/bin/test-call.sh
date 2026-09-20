#!/usr/bin/env bash
# Place a test call out through the carrier, with a live SIP trace.
#
#   ./asterisk/bin/test-call.sh 9779812345678
#
# The called phone should ring and, when answered, play a short prompt. That
# proves signalling, authentication, media, and NAT traversal all work in the
# outbound direction.
set -euo pipefail

CONTAINER="${CONTAINER:-asterisk-pana}"
NUMBER="${1:-}"

if [ -z "$NUMBER" ]; then
    echo "usage: $0 <number in the format your carrier expects>" >&2
    echo "For NTC Nepal that is usually the full number without a leading +." >&2
    exit 1
fi

echo "Enabling the SIP trace, then calling $NUMBER."
echo "The trace prints full SIP messages, which include the Authorization"
echo "header. Do not paste this output anywhere without removing it."
echo

docker exec "$CONTAINER" asterisk -rx 'pjsip set logger on' >/dev/null

# Originate from the trunk to the number, landing in to-carrier so the
# answered call plays a recognisable prompt rather than silence.
docker exec "$CONTAINER" asterisk -rx \
    "channel originate PJSIP/${NUMBER}@carrier application Playback hello-world"

echo
echo "Watching for 30 seconds. Ctrl-C to stop early."
timeout 30 docker logs -f --since 5s "$CONTAINER" 2>&1 \
    | grep -viE "declined to load|Unable to load config file" || true

docker exec "$CONTAINER" asterisk -rx 'pjsip set logger off' >/dev/null
echo
echo "Trace off. If the call failed, the SIP response code above says why:"
echo "  401/407  authentication -- unexpected here, registration works"
echo "  403      the carrier refused the call (number format, or barred)"
echo "  404      the carrier did not recognise the number"
echo "  488      codec mismatch -- the carrier wants something other than ulaw/alaw"
echo "  no audio NAT: check SIP_EXTERNAL_IP and that RTP 20000-20099 is forwarded"
