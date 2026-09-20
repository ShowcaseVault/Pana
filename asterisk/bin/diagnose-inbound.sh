#!/usr/bin/env bash
# Answer one question: when you ring the DID, does the call reach this host?
#
# Watches three layers at once, because each one rules out a different cause:
#
#   packets    an INVITE arriving on UDP 5060 at all -- if nothing appears
#              here, the problem is upstream (carrier, NAT, firewall) and
#              no amount of Asterisk configuration will fix it
#   SIP        what Asterisk made of that INVITE, and what it replied
#   dialplan   whether the call reached from-carrier and was accepted
#
# Run it, then ring the DID from any phone.
set -euo pipefail

CONTAINER="${CONTAINER:-asterisk-pana}"
SECONDS_TO_WATCH="${SECONDS_TO_WATCH:-60}"
CAP_DIR="$(mktemp -d)"
CAP="$CAP_DIR/sip.pcap"

cleanup() {
    docker exec "$CONTAINER" asterisk -rx 'pjsip set logger off' >/dev/null 2>&1 || true
    [ -n "${TCPDUMP_PID:-}" ] && kill "$TCPDUMP_PID" 2>/dev/null || true
    wait "${TCPDUMP_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT

DID=$(docker exec "$CONTAINER" asterisk -rx 'dialplan show globals' 2>/dev/null \
      | sed -n 's/.*CARRIER_DID=\(.*\)/\1/p' | tr -d '\r')

echo "Watching for ${SECONDS_TO_WATCH}s. Ring ${DID:-your DID} now."
echo

if ! sudo -n true 2>/dev/null; then
    echo "Packet capture needs sudo. You will be prompted once."
fi
sudo tcpdump -i any -n -s 0 -w "$CAP" 'udp port 5060' >/dev/null 2>&1 &
TCPDUMP_PID=$!

docker exec "$CONTAINER" asterisk -rx 'pjsip set logger on' >/dev/null

# Asterisk's own view, streamed live so you see the call as it happens.
timeout "$SECONDS_TO_WATCH" docker logs -f --since 1s "$CONTAINER" 2>&1 \
    | grep -viE "declined to load|Unable to load config file" \
    | grep -iE "invite|inbound call|rejecting|answer|playback|hangup|unmatched|<---|--->" \
    || true

cleanup
sleep 1

echo
echo "================ what arrived on the wire ================"
INVITES=$(sudo tcpdump -r "$CAP" -n 2>/dev/null | grep -c "INVITE" || true)
TOTAL=$(sudo tcpdump -r "$CAP" -n 2>/dev/null | wc -l || echo 0)

echo "SIP packets seen: $TOTAL, of which INVITE: $INVITES"
echo

if [ "$INVITES" -gt 0 ]; then
    echo "An INVITE reached this host, so the call is arriving."
    echo "If it still failed, the cause is on our side -- read the SIP trace"
    echo "above for the response code we sent back."
    echo
    echo "Who sent it:"
    sudo tcpdump -r "$CAP" -n 2>/dev/null | grep "INVITE" | head -3
else
    echo "No INVITE arrived. The call never reached this host, so nothing in"
    echo "the Asterisk configuration can be the cause. In order of likelihood:"
    echo
    echo "  1. The carrier is not routing the DID to this trunk at all."
    echo "     Ask them to confirm the number points at your SIP registration."
    echo "  2. The router is not forwarding UDP 5060 to this host, and the"
    echo "     registration pinhole is not being reused by the carrier."
    echo "  3. A firewall on this host is dropping it (check: sudo ufw status)."
    echo "  4. Your ISP uses CGNAT, in which case inbound cannot be forwarded"
    echo "     and the registration path is the only option."
    echo
    if [ "$TOTAL" -gt 0 ]; then
        echo "Other SIP traffic was seen, so the port itself is live:"
        sudo tcpdump -r "$CAP" -n 2>/dev/null | head -3
    else
        echo "No SIP traffic at all -- not even registration refreshes."
    fi
fi

echo
echo "Capture kept at: $CAP"
echo "Inspect with: sudo tcpdump -r $CAP -nA | less"
echo "It contains Authorization headers; delete it when done."
