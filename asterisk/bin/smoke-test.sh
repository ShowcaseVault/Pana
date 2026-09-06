#!/usr/bin/env bash
# Prove the trunk works, in order of increasing commitment:
#   1. the rendered config holds no unsubstituted placeholders
#   2. the container is running and Asterisk answers
#   3. the carrier accepted our registration
#   4. the carrier endpoint answers OPTIONS (qualify)
#
# Step 3 is the one that matters: "Registered" means the credentials are
# correct and the carrier will route calls to us.

set -euo pipefail

CONTAINER="${CONTAINER:-asterisk-pana}"

run() { docker exec "$CONTAINER" asterisk -rx "$1"; }

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "== 1. rendered configuration =="
# Read the rendered file's shape without printing it: it holds the password.
if docker exec "$CONTAINER" grep -q '\${' /etc/asterisk/pjsip.conf; then
    fail "pjsip.conf contains unsubstituted \${...} placeholders"
fi
perms=$(docker exec "$CONTAINER" stat -c '%a %U' /etc/asterisk/pjsip.conf)
[[ "$perms" == "600 asterisk" ]] || fail "pjsip.conf is '$perms', expected '600 asterisk'"
echo "ok: rendered, mode 600, owned by asterisk"

echo
echo "== 2. asterisk is up =="
run 'core show uptime' >/dev/null || fail "Asterisk is not responding to CLI commands"
echo "ok: $(run 'core show version')"

echo
echo "== 3. carrier registration =="
reg=$(run 'pjsip show registrations')
echo "$reg"
if grep -q 'Registered' <<<"$reg"; then
    echo "ok: registered with the carrier"
elif grep -q 'Rejected\|Forbidden' <<<"$reg"; then
    fail "the carrier rejected our credentials (check SIP_AUTH_NAME and SIP_PASSWORD)"
else
    fail "not registered yet; if this is a fresh start, wait and retry"
fi

echo
echo "== 4. carrier endpoint reachability =="
run 'pjsip show aors' | grep -i carrier || true
contacts=$(run 'pjsip show contacts')
echo "$contacts"
grep -q 'Avail' <<<"$contacts" \
    || echo "warn: the carrier contact is not marked Avail; some carriers do not answer OPTIONS, which is harmless if step 3 passed"

echo
echo "All checks passed. The trunk is registered."
echo "Next: ask the carrier to send a test call to your DID and watch:"
echo "  docker logs -f $CONTAINER"
