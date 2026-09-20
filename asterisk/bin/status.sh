#!/usr/bin/env bash
# A snapshot of the trunk: is it registered, are calls up, what happened
# recently. Safe to run at any time; places no calls and prints no secrets.
set -euo pipefail
CONTAINER="${CONTAINER:-asterisk-pana}"
run() { docker exec "$CONTAINER" asterisk -rx "$1" 2>&1; }

echo "=== container ==="
docker ps --filter "name=$CONTAINER" --format '{{.Status}}' || echo "not running"

echo
echo "=== trunk ==="
run 'pjsip show registrations' | grep -iE "carrier|Registered|Unregistered|Rejected" || echo "no registration"

echo
echo "=== endpoint (state, and channels in use of the cap) ==="
run 'pjsip show endpoints' | grep -E "carrier " || true

echo
echo "=== limits in force ==="
run 'dialplan show globals' | grep -E "MAX_CALL_SECONDS|CARRIER_DID" || true

echo
echo "=== calls right now ==="
run 'core show channels' | tail -3

echo
echo "=== inbound calls seen since start ==="
# The dialplan logs one NoOp per inbound call, so the log is the call history
# until CDRs are wired up.
accepted=$(docker logs "$CONTAINER" 2>&1 | grep -c "Inbound call from" || true)
rejected=$(docker logs "$CONTAINER" 2>&1 | grep -c "Rejecting call to" || true)
echo "arrived: $accepted   rejected as not-our-DID: $rejected"
docker logs "$CONTAINER" 2>&1 | grep -E "Inbound call from|Rejecting call to" | tail -5 \
    || echo "(none yet -- no inbound call has reached the dialplan)"
