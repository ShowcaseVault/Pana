# Telephony incidents

Every telephony fault that has actually happened, what caused it, and what
fixed it. Find your symptom in the index, read that entry, and check the
"ruled out" list before trying anything new. Every wrong turn here cost hours,
and several of them looked convincing at the time.

The operating guide -- setup, testing, the "not registered" runbook -- is
[telephony.md](telephony.md). This page is the history behind it.

## Index

| What you see | Entry |
|---|---|
| Caller hears NTC's "the number you have dialed is not registered"; we say `Registered` | [1](#1-stale-public-address), [5](#5-inbound-not-registered-with-everything-clean) |
| Call connects, caller hears Pana, Pana records 0 bytes ("could not hear you") | [2](#2-ims-sends-no-audio) |
| A config fix has no effect; the rendered `pjsip.conf` does not match the entrypoint | [3](#3-container-running-a-stale-image) |
| Every outbound call: `183` with `cause=1` "Unallocated (unassigned) number" | [4](#4-outbound-calls-rejected-as-unallocated-number) |
| An env knob is ignored, always its default | [6](#6-env-knobs-that-never-reached-the-container) |
| Caller hears a whistle instead of Pana | [7](#7-whistle-instead-of-pana) |
| Test call shows as a private number | [8](#8-test-calls-show-as-a-private-number) |

## How to debug, in the order that would have been fastest

1. **Is the running container the current code?** Run `make asterisk-up`, which
   rebuilds and detects the network. Then compare
   `docker exec asterisk-pana md5sum /usr/local/bin/entrypoint.sh` against
   `md5sum asterisk/bin/entrypoint.sh`.
2. **Does the INVITE reach us?** `pjsip set logger on`, call, and look for
   `INVITE sip:+977...`. This splits every inbound problem in two. No INVITE
   means the carrier did not send it, and no Asterisk or NAT setting is the
   cause until proven otherwise.
3. **Does a softphone work on the same account and network?** If Zoiper
   works, the account, the carrier and the network are fine, and the fault is
   in what we send. Compare our messages with what a softphone sends.
4. **Change one thing per test call.** Wait three to four minutes after a
   restart before calling, so the test exercises the steady state and not a
   freshly opened NAT mapping.
5. **Compare values only within one call.** A port in a packet capture and a
   port in a SIP trace mean nothing together unless they share a Call-ID.

Two traps in the tooling:

- The SIP logger is off again after every container restart, and
  `test-call.sh` turns it off when it finishes. Re-run `pjsip set logger on`
  before every traced call.
- `pjsip send register` sends `Expires: 0` first and de-registers the trunk.
  Wait for the natural refresh (`SIP_REGISTRATION_EXPIRY`, 120s) instead.

## 1. Stale public address

**2026-09-20.** Caller hears "the number you have dialed is not registered";
`pjsip show registrations` says `Registered`.

**Cause.** The host moved to a new connection, but `secrets/sip_trunk.env`
still pinned the old public IP and LAN. REGISTER is outbound, so it succeeds
whatever address we claim. The carrier then sent INVITEs to an address that
was no longer ours.

**Fix.** `make asterisk-up` detects the public IP (over HTTPS) and the LAN
(from the host's link routes) on every start, and passes both to the
container, where they override the secret file. Leave `SIP_EXTERNAL_IP` and
`SIP_LOCAL_NET` empty in the secret file.

**Verify.** The addresses `make asterisk-up` prints match
`curl -4 -s ident.me` and `ip route get 1.1.1.1`.

## 2. IMS sends no audio

**2026-10-15.** The call connects and the caller hears Pana, but every turn
records nothing (`recorded 0 bytes`) and Pana keeps saying it could not hear.

**Cause.** We described ourselves two ways in one call: a private address in
SIP (`Contact: <sip:192.168.100.59:5060>`) and a public one in SDP
(`c=IN IP4 49.244.163.169`). NTC's IMS answers that contradiction by sending
no RTP at all, while SIP carries on normally. In the captures, about 300 RTP
packets went out per call and none came back.

**Fix.** `SIP_NAT_MODE=latch`, the default. Asterisk advertises no external
address, so SIP and SDP agree, and the carrier latches onto the address our
packets actually come from, as it does for a softphone. This depends on
`rtp_symmetric` and `force_rport` on the endpoint (both on).

**Verify.** Set `VOICE_KEEP_RECORDINGS=true`, which logs bytes per turn. A
non-zero count proves the media path. Turn it off afterwards: it keeps
recordings of real conversations. `scripts/rtp_probe.py` records one call
through ARI alone, so a zero-byte result places the fault below the
application.

**How it was found.** By comparing our REGISTER, header by header, with how a
softphone on the same network and account behaves. Hours were lost first on
blaming the carrier, the firewall and `stunaddr`; see the ruled-out list.

**Earlier one-way audio (September).** The same symptom on the `103.129.134.x`
connection was put down to the NAT rewriting RTP ports, with the conclusion
that it "needs a routable address or a tunnel". That conclusion was wrong: on
2026-10-29 that same connection carried two-way audio under `latch`. The
September config advertised external addresses, so the likelier cause was the
same contradiction as above.

## 3. Container running a stale image

**2026-10-29.** Fixes in `asterisk/bin/entrypoint.sh` had no effect. The
rendered `/etc/asterisk/pjsip.conf` showed `external_media_address` and a
month-old `local_net`, although the container's environment said `latch`.

**Cause.** The entrypoint is baked into the image. `make asterisk-up` ran
`docker compose up -d`, which reuses an existing image even when its build
context has changed. The container was running an image built on 2026-09-20,
so the 2026-10-15 latch fix had never run on that machine.

**Fix.** `make asterisk-up` runs `up -d --build`. When nothing changed, the
rebuild is a cache hit.

**Verify.** The `md5sum` comparison in step 1 above.

## 4. Outbound calls rejected as "Unallocated number"

**2026-10-29.** Every outbound call, whatever the number format (`98XXXXXXXX`,
`97798XXXXXXXX`, `+97798XXXXXXXX`), got `183 Session Progress` carrying
`Reason: Q.850;cause=1;text="Unallocated (unassigned) number"` and an
announcement. Zoiper on the same account could call out fine.

**Cause.** The Request-URI named the proxy IP: `INVITE
sip:98XXXXXXXX@202.70.74.178`. The AOR contact was `sip:<proxy>` and the
endpoint had no `outbound_proxy`. NTC's IMS rejects that form.

**Fix.** In `pjsip.conf.template`, the AOR contact is `sip:${SIP_DOMAIN}` and
both the endpoint and the AOR send via
`outbound_proxy = sip:${SIP_OUTBOUND_PROXY}\;lr`. The Request-URI now reads
`INVITE sip:98XXXXXXXX@ims.ntc.net.np` with a `Route` to the proxy, which is
what a softphone sends. The `\;` matters: an unescaped `;` starts a comment in
Asterisk config, and `lr` would be silently dropped.

**Verify.** `make asterisk-call NUMBER=98XXXXXXXX` rings the phone (`180
Ringing`, `200 OK`).

## 5. Inbound "not registered" with everything clean

**2026-10-29.** After entries 3 and 4 were fixed: `Registered`, correct
detected addresses, no softphone registered. Callers still heard "not
registered", and no INVITE reached Asterisk. Carrier NOTIFYs (`Event:
ua-profile`) arrived after every REGISTER, so the path from the carrier to us
was open. The IMS was choosing not to deliver the call.

**What fixed it.** Inbound started working after a Zoiper session on the same
account: Zoiper registered, made and received calls, then was force-stopped,
and Asterisk re-registered. It kept working through isolation tests, each with
a three to four minute wait before calling: keepalive OPTIONS addressed to the
proxy IP, to the domain, and keepalive turned off entirely.

**Not isolated.** Exactly what that session reset on NTC's side is unknown.
The first successful outbound call (entry 4) happened in the same window and
cannot be excluded. If this recurs, step 5 of the runbook in telephony.md
(register a softphone, call each way, force-stop, wait, retry) is the known
remedy. Note how this incident unfolds, and do not repeat the hours spent on
the ruled-out list below.

## 6. Env knobs that never reached the container

**2026-10-29.** `SIP_KEEPALIVE_INTERVAL` and `SIP_REGISTRATION_EXPIRY` were
read by the entrypoint but never listed in `docker-compose.asterisk.yml`, so
setting them in the shell changed nothing. Both are listed now, alongside
`SIP_QUALIFY_FREQUENCY`.

Values in `secrets/sip_trunk.env` also reach the entrypoint, since it sources
that file, and they override compose values. The exceptions are the detected
`SIP_EXTERNAL_IP` and `SIP_LOCAL_NET`.

`keep_alive_interval` (`SIP_KEEPALIVE_INTERVAL`) is sent only on TCP and TLS.
On this UDP trunk it does nothing. The UDP keepalive is `SIP_QUALIFY_FREQUENCY`:
an OPTIONS to the carrier every 20s, which NTC answers with `200 OK`. It is on
as protection against NAT expiry, but turning it off did not break inbound
(entry 5).

## 7. Whistle instead of Pana

The dialplan plays `cid_whistle` when `Stasis(pana-voice)` cannot hand the call
to the voice service. Everything below the application worked: the carrier
routed the call, the INVITE arrived, `identify` matched and the call was
answered. Start `make voice` and confirm with `ari show apps`, which must list
`pana-voice`.

The voice service does not reconnect. When Asterisk restarts (every
`make asterisk-up` recreates the container), the ARI WebSocket closes and
`make voice` exits with status 0, logging nothing about it. Restart
`make voice` after every `make asterisk-up`.

## 8. Test calls show as a private number

`make asterisk-call` uses a CLI originate, which carries no caller ID, so
Asterisk sends `From: "Anonymous"` and the phone shows "private number".
Calls through the dialplan or ARI carry the endpoint's `callerid`. The trunk's
own number is `SIP_USERNAME` (`+97760410099`).

## Ruled out

Each was tested on live calls and did not fix the problem it was blamed for.
Rule them back in only with new evidence.

| Suspect | Why it is not the answer |
|---|---|
| NAT rewriting SIP or RTP ports | The `103.129.134.x` connection rewrites ports and carries two-way calls under `latch`. A STUN probe of Google's server says nothing about the path to the carrier; the probe script that claimed otherwise was deleted. |
| CGNAT | The IMS stores a CGNAT address (`100.105.32.136`) as our contact, and calls reach us there. |
| `SIP_NAT_MODE` for "not registered" | `latch`, external-address and STUN-media modes all failed the same way before entry 5's reset. `latch` works after it. |
| Keepalive frequency | `keep_alive_interval` does nothing on UDP. Qualify on or off made no difference to inbound. |
| Binding a high SIP port | The NAT rewrote it as well; no effect. |
| "Needs a VPS or tunnel" | Concluded twice, wrong both times. Everything works on the plain home connection. |
| The carrier is at fault | A softphone on the same account and network works. Look at what we send first. |
| Host firewall | `ufw` was inactive. tcpdump sits below netfilter, so a firewall drop still shows up in a capture. |
| `stunaddr` poisoning the SDP | The ports compared came from two different calls. Within one call they matched. |
| `local_net` harmful | Clearing it changed nothing. It only exempts LAN destinations, and the carrier is not on the LAN. |
