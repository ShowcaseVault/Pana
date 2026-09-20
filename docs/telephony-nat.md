# Inbound audio does not work from this network

**Status:** unresolved on the development connection. Not a code defect — every
layer of the application is working. Needs a host with a routable public IPv4.

Inbound calls connect, the caller hears Pana, and Pana hears nothing. This is a
record of how that was diagnosed, which explanations were ruled out, and what
would actually fix it, so the next person does not repeat the search.

## The symptom

A call arrives, is answered, and the greeting plays. Every turn then records
zero bytes:

    call 1789884646.8: recorded 0 bytes (0.0s)
    call 1789884646.8: nothing heard (1 of 3)
    call 1789884646.8: recorded 0 bytes (0.0s)
    call 1789884646.8: nothing heard (2 of 3)

Asterisk reports the same thing from its own side:

    WARNING app.c:1941 __ast_play_and_record:
        No audio available on PJSIP/carrier-00000004??

Audio flows to the caller and never back. One-way media.

## What was ruled out, and how

Each of these was a plausible cause and each was tested rather than reasoned
about. They are listed because the evidence is what makes the conclusion
trustworthy, not the conclusion itself.

**Speech recognition.** Tested directly by synthesising a known phrase with
Magpie, converting to 8 kHz u-law -- exactly what Asterisk records -- and
sending it to Groq. It transcribes correctly, including under conditions far
worse than a phone line:

| Input | Transcript |
|---|---|
| clean | exact |
| −18 dB | exact |
| −30 dB | exact |
| heavy line noise | exact |
| 50% packet loss | exact |

Recognition cannot be the problem: nothing reaches it.

**The pipeline.** `scripts/rtp_probe.py` answers one call and records ten
seconds through ARI alone -- no recognition, no synthesis, no turn loop. It
returns zero bytes. The fault is below the application entirely.

**The trunk.** Registration is healthy (`pjsip show registrations` reports
`Registered`), the carrier is reachable (45 ms, no loss), the dialplan matches
the DID, and the call reaches `Stasis`. Signalling is fine.

**A stale public address.** This *was* a real fault and is fixed. The external
address in `secrets/sip_trunk.env` was pinned to an address the ISP had since
reassigned, so inbound calls were routed to an address that was no longer ours
and never arrived at all. `make asterisk-up` now detects the public address at
start and passes it in (see `SIP_EXTERNAL_IP` in the Makefile and
`asterisk/bin/entrypoint.sh`). Fixing it made calls connect; it did not fix
media.

## The cause

The SDP Asterisk offers the carrier names the address correctly and the port
incorrectly:

    c=IN IP4 103.129.134.143      <- correct public address
    m=audio 20086 RTP/AVP 8 108   <- Asterisk's INTERNAL port

The NAT in front of this connection rewrites source ports. Measured with STUN:

    local :20030  ->  103.129.134.143:43093
    local :20050  ->  103.129.134.143:50804

So the carrier is told to send audio to `103.129.134.143:20086`, a port that is
not open on the public side. The packets are dropped before they reach us.

Outbound works because Asterisk sends first and the NAT creates a mapping on
the way out. Inbound has no such mapping to use.

## Why it cannot be configured around

`external_media_address` and `stunaddr` are the two settings that exist for
this, and neither supplies a mapped port on Asterisk 18.

| Configuration | SDP advertises | Result |
|---|---|---|
| `external_media_address` set | `103.129.134.143:20086` | right address, internal port -- dropped |
| unset, hoping STUN applies | `192.168.1.11:20086` | private address -- worse |

`external_media_address` rewrites the SDP after RTP has filled it in, and it
knows only the address, not the port. Removing it does not fall back to STUN:
PJSIP builds media addresses from the transport, and `stunaddr` in `rtp.conf`
never reaches that path. Both were tried on live calls; the second is the
regression that advertised the private address.

A further measurement rules out the remaining hope. The mapping is stable while
a socket is open, but a new socket on the same local port gets a new external
port:

    same local port 20060, one live socket:  43894, 43894, 43894
    port 20030 measured on two occasions:    29189, then 43093

Asterisk allocates a fresh RTP socket per call, so even a correct STUN lookup
would describe a mapping that no longer exists by the time the carrier sends.

`rtp_symmetric`, `force_rport` and `rewrite_contact` are all enabled and
correct. They handle a NAT that preserves ports. This one does not.

## What is still in the tree from this work

Kept because it is correct on a host with a public address, and inert here:

- `stunaddr` and `rtpkeepalive` in `asterisk/rtp.conf`
- `SIP_MEDIA_VIA_STUN` in `asterisk/bin/entrypoint.sh` and
  `docker-compose.asterisk.yml`, default `false`. Setting it `true` drops
  `external_media_address`; on this network that advertises the private
  address, so leave it off.
- `VOICE_KEEP_RECORDINGS` -- keeps each turn's recording instead of deleting
  it and logs its size. Zero bytes distinguishes a media path problem from a
  recognition one in one line of log. Off by default; these are recordings of
  real conversations.
- `scripts/rtp_probe.py` -- the isolation test. Run it before assuming any
  future audio fault is in the pipeline.

## What would fix it

The requirement is one routable public IPv4 with unrestricted UDP on 5060 and
20000-20099. The trunk authenticates by username and password, not by source
address, so it registers from anywhere -- which is what makes every option
below viable.

1. **A public IP from NTC on this line.** Cheapest, paid locally, no
   infrastructure, no added latency. Ask whether the plan offers one.
2. **A rented server.** Any VPS or cloud VM with a dedicated IP. Asterisk moves
   there; the config in this repo works unchanged. Run the voice service on the
   same host rather than leaving it here, or every turn crosses the network
   twice.
3. **WireGuard to a rented server.** Keeps Asterisk local: the server forwards
   SIP and RTP over the tunnel and Asterisk advertises the server's address.
   More moving parts, useful if Asterisk must stay on a development machine.

Two things to confirm with any provider before paying, since budget hosts
block both: **is UDP unrestricted on arbitrary ports**, and **is SIP/VoIP
permitted**. Either answer being no makes the host useless for this.

Choose a region by latency. Nepal to Singapore or Mumbai is roughly 50-100 ms;
Nepal to the US is 250-350 ms, and conversation becomes difficult past about
300 ms because both sides start talking over each other.

**Platform-as-a-service will not work.** Render, Railway, Vercel, Heroku and
Cloud Run expose HTTP and TCP only. SIP and RTP are UDP, so none of them can
carry this.

## Developing without any of that

Only the telephony leg is blocked. Recognition, generation, synthesis, the turn
loop and the companion behaviour are all independent of it and all working, and
that is where the remaining work is. A microphone-driven loop over the same
`stt`/`llm`/`tts` seams exercises everything except Asterisk and iterates far
faster than a phone call.
