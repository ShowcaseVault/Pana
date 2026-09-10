#!/bin/sh
# Render the Asterisk configuration that contains secrets, then hand off to
# Asterisk itself.
#
# The trunk password reaches this script through an environment file that is
# mounted read-only, and leaves it only in /etc/asterisk/pjsip.conf, which is
# created 0600 and owned by the asterisk user. It is never written to an image
# layer, never printed, and never passed on a command line (where it would be
# visible in the process table to every other process in the container).

set -eu

SECRET_FILE="${SIP_SECRET_FILE:-/run/secrets/sip_trunk.env}"
TEMPLATE="/etc/asterisk/templates/pjsip.conf.template"
RENDERED="/etc/asterisk/pjsip.conf"

if [ ! -r "$SECRET_FILE" ]; then
    echo "entrypoint: cannot read $SECRET_FILE" >&2
    echo "entrypoint: copy secrets/sip_trunk.env.example to secrets/sip_trunk.env," >&2
    echo "entrypoint: fill it in, and chmod 600 it." >&2
    exit 1
fi

# Refuse a world-readable secret. Every other user in the container (and, via
# the bind mount, on the host) could otherwise read the trunk password.
mode=$(stat -c '%a' "$SECRET_FILE")
# Pad to four digits so the group and other digits are always in a known
# position, then require both to be 0.
padded=$(printf '%04d' "$mode")
group_other=$(printf '%s' "$padded" | cut -c3-4)
if [ "$group_other" != "00" ]; then
    echo "entrypoint: $SECRET_FILE is mode $mode, which grants access to group" >&2
    echo "entrypoint: or other. Run: chmod 600 secrets/sip_trunk.env" >&2
    exit 1
fi

# shellcheck disable=SC1090
. "$SECRET_FILE"

for var in SIP_USERNAME SIP_PASSWORD SIP_AUTH_NAME SIP_DOMAIN SIP_OUTBOUND_PROXY; do
    eval "value=\${$var:-}"
    if [ -z "$value" ]; then
        echo "entrypoint: $var is empty in $SECRET_FILE" >&2
        exit 1
    fi
done

SIP_TRANSPORT="${SIP_TRANSPORT:-udp}"
case "$SIP_TRANSPORT" in
    udp|tcp|tls) ;;
    *) echo "entrypoint: SIP_TRANSPORT must be udp, tcp or tls (got '$SIP_TRANSPORT')" >&2; exit 1 ;;
esac

# The concurrency cap. Lower it and a leaked credential costs less; the
# default of 2 suits a single-line trunk and should be raised deliberately.
SIP_MAX_CHANNELS="${SIP_MAX_CHANNELS:-2}"

# The per-call ceiling, in seconds. Two things make this matter: carrier
# minutes on a billable call, and a channel plus its media session held open
# on our side. A call that hits the limit is hung up, so pick a value above
# any legitimate conversation length.
SIP_MAX_CALL_SECONDS="${SIP_MAX_CALL_SECONDS:-180}"

# NAT keepalive. Behind carrier-grade NAT the IPv4 translation is torn down
# after a short idle period and no port forward can be configured, so holding
# the mapping open is the only way inbound calls can arrive at all. 30s is
# below the timeout most CGNAT deployments use; the registration expiry is
# kept short for the same reason.
SIP_KEEPALIVE_INTERVAL="${SIP_KEEPALIVE_INTERVAL:-30}"
SIP_REGISTRATION_EXPIRY="${SIP_REGISTRATION_EXPIRY:-120}"
case "$SIP_MAX_CALL_SECONDS" in
    ''|*[!0-9]*)
        echo "entrypoint: SIP_MAX_CALL_SECONDS must be a whole number of seconds" >&2
        echo "entrypoint: (got '$SIP_MAX_CALL_SECONDS')" >&2
        exit 1
        ;;
esac
if [ "$SIP_MAX_CALL_SECONDS" -lt 10 ]; then
    echo "entrypoint: SIP_MAX_CALL_SECONDS is ${SIP_MAX_CALL_SECONDS}s, which would cut off" >&2
    echo "entrypoint: calls before they are usable. Refusing to start." >&2
    exit 1
fi

# The dialplan reads this as a global, so the limit lives in one place rather
# than being duplicated at every Answer().
DIALPLAN_GLOBALS="MAX_CALL_MS = $((SIP_MAX_CALL_SECONDS * 1000))
MAX_CALL_SECONDS = ${SIP_MAX_CALL_SECONDS}
CARRIER_DID = ${SIP_USERNAME}"

# NAT handling. Only emitted when an external IP was supplied, because
# external_media_address with an empty value makes Asterisk advertise a blank
# address in SDP and one-way audio is the result.
NAT_TRANSPORT_LINES=""
if [ -n "${SIP_EXTERNAL_IP:-}" ]; then
    NAT_TRANSPORT_LINES="external_media_address = ${SIP_EXTERNAL_IP}
external_signaling_address = ${SIP_EXTERNAL_IP}"
    if [ -n "${SIP_LOCAL_NET:-}" ]; then
        NAT_TRANSPORT_LINES="${NAT_TRANSPORT_LINES}
local_net = ${SIP_LOCAL_NET}"
    fi
fi

# The outbound proxy needs the full URI form, and it belongs on both the
# registration and the identify match so that replies from the proxy are
# recognised as the carrier.
proxy_host="${SIP_OUTBOUND_PROXY%%:*}"
# The lr parameter marks this as a loose route, which is what an outbound
# proxy requires; the semicolon is literal and must not be shell-escaped.
REG_PROXY_LINE="outbound_proxy = sip:${SIP_OUTBOUND_PROXY};lr"
# Which addresses count as "the carrier" for inbound calls.
#
# Asterisk resolves every match value when it loads the config, and discards
# the whole identify object if any one of them fails to resolve. On an IMS
# network SIP_DOMAIN is typically a realm (an identity namespace) with no A
# record at all, so including it unconditionally would drop the object and,
# with it, every inbound call -- while outbound registration kept working, so
# the breakage would not be obvious. Include the domain only when it actually
# resolves; the proxy address is what sends us traffic in any case.
IDENTIFY_MATCH="$proxy_host"
if [ "$proxy_host" != "$SIP_DOMAIN" ]; then
    if getent hosts "$SIP_DOMAIN" >/dev/null 2>&1; then
        IDENTIFY_MATCH="${SIP_DOMAIN},${proxy_host}"
    else
        echo "entrypoint: $SIP_DOMAIN does not resolve; matching inbound calls" >&2
        echo "entrypoint: on the outbound proxy address ($proxy_host) only." >&2
        echo "entrypoint: If the carrier sends calls from other addresses, add" >&2
        echo "entrypoint: them to SIP_IDENTIFY_EXTRA in secrets/sip_trunk.env." >&2
    fi
fi

# Additional carrier addresses, when signalling arrives from a range wider than
# the outbound proxy. Ask the carrier for these rather than guessing: an entry
# here is an address allowed to place calls into our dialplan.
if [ -n "${SIP_IDENTIFY_EXTRA:-}" ]; then
    IDENTIFY_MATCH="${IDENTIFY_MATCH},${SIP_IDENTIFY_EXTRA}"
fi

export SIP_USERNAME SIP_PASSWORD SIP_AUTH_NAME SIP_DOMAIN SIP_OUTBOUND_PROXY \
       SIP_TRANSPORT SIP_MAX_CHANNELS SIP_KEEPALIVE_INTERVAL SIP_REGISTRATION_EXPIRY NAT_TRANSPORT_LINES REG_PROXY_LINE \
       IDENTIFY_MATCH

# Create the file empty and locked down *before* any secret goes into it, so
# there is no window in which it exists with looser permissions.
umask 077
: > "$RENDERED"
chmod 600 "$RENDERED"
chown asterisk:asterisk "$RENDERED"

envsubst < "$TEMPLATE" >> "$RENDERED"

cat >> "$RENDERED" <<'HARDENING'

; --- Global hardening ------------------------------------------------------

[global]
type = global
; Do not advertise the version string: it tells a scanner exactly which CVEs
; are worth trying against this host.
user_agent = Pana
; Send a blank packet on every transport at this interval so a NAT translation
; stays alive between re-registrations. This is a global option, not a
; transport one. Behind carrier-grade NAT it is what keeps inbound calls
; arriving at all: once the mapping expires the carrier's INVITE has nowhere
; to go, while our registration still looks perfectly healthy.
keep_alive_interval = KEEPALIVE_PLACEHOLDER
; Anonymous inbound calls are refused by construction rather than by a
; setting: the only `identify` section matches the carrier, so traffic from
; anywhere else matches no endpoint and is rejected. Adding an endpoint named
; `anonymous` would undo that, so do not.

[system]
type = system
; Bound how long a failed transaction is retried, so a flood of registration
; attempts cannot exhaust the transaction table.
timer_t1 = 500
timer_b = 32000
HARDENING

# The dialplan's globals are rendered rather than baked in, so the call limit
# can change with an environment variable instead of an image rebuild.
umask 022
printf '%s\n' "[globals]" > /etc/asterisk/extensions_globals.conf
printf '%s\n' "$DIALPLAN_GLOBALS" >> /etc/asterisk/extensions_globals.conf
chown asterisk:asterisk /etc/asterisk/extensions_globals.conf

sed -i "s/KEEPALIVE_PLACEHOLDER/${SIP_KEEPALIVE_INTERVAL}/" "$RENDERED"

# ARI records into this directory and will not create it. The Debian package
# does not ship it, and /var/spool/asterisk is a named volume, so creating it
# in the Dockerfile would be masked at run time -- it has to happen here, on
# every start. Without it every /channels/<id>/record returns a 500 whose only
# explanation is "No such file or directory" in the Asterisk log.
install -d -o asterisk -g asterisk -m 750 /var/spool/asterisk/recording

# Generated speech arrives through a bind mount from the host, so this
# directory is deliberately NOT created or chowned here: the writer is the
# voice service running as the host user, and taking ownership for the
# container's asterisk uid (101) is what locks that writer out. Asterisk only
# ever reads from it, and world-readable files are enough for that.

# ARI credentials for the voice service. Supplied through the environment from
# .env, so Asterisk and the voice service read one value from one place -- a
# password generated in here could not be shared without also being exported.
# Required: ARI can originate calls, so it must never fall back to a default.
if [ -z "${ARI_PASSWORD:-}" ]; then
    echo "ARI_PASSWORD is not set. Add it to .env (see .env.example)." >&2
    exit 1
fi
export ARI_PASSWORD

umask 077
: > /etc/asterisk/ari.conf
chmod 600 /etc/asterisk/ari.conf
chown asterisk:asterisk /etc/asterisk/ari.conf
envsubst < /etc/asterisk/templates/ari.conf.template >> /etc/asterisk/ari.conf

# Drop the secrets from the environment before exec'ing Asterisk, so they do
# not appear in /proc/<pid>/environ for the long-running process.
unset SIP_PASSWORD SIP_AUTH_NAME SIP_USERNAME ARI_PASSWORD

exec /usr/sbin/asterisk -f -U asterisk -G asterisk -vvv
