# Inbound audio and the NAT'd development network

**Status:** resolved 2026-10-15. The fix is `SIP_NAT_MODE=latch`, which is the
default in `docker-compose.asterisk.yml`. If inbound audio is failing again,
read "The second occurrence" below before changing any setting.

Inbound calls connect and the caller hears Pana; whether Pana hears the caller
has failed twice, on two different connections, for two unrelated reasons. The
symptom is identical both times, which is the trap: the second occurrence was
initially diagnosed as a recurrence of the first, and that cost an evening.

This document is in two halves.

- **The second occurrence (2026-10-15)** — resolved. The NAT was innocent. We
  were sending the carrier a self-contradictory offer and it responded by
  sending no media at all. Start here.
- **The first occurrence** — unresolved at the time, on a connection whose NAT
  rewrote RTP ports. That analysis is still correct *for that kind of NAT* and
  is kept from "The first occurrence" onwards.

One measurement separates them:

```
python3 scripts/stun_probe.py
```

A mapped port that differs from the local port means the NAT rewrites ports
and the first occurrence applies. A mapped port equal to the local port means
the NAT is not your problem and the second occurrence does.

## The symptom, both times

A call arrives, is answered, the greeting plays, and every turn records
nothing:

    call 1792065296.10: recorded 0 bytes (0.0s)
    call 1792065296.10: nothing heard (1 of 3)

Audio flows to the caller and never back. One-way media. Set
`VOICE_KEEP_RECORDINGS=true` to get the byte count on every turn; zero
distinguishes a media path fault from a recognition one in a single log line.

---

# The second occurrence, 2026-10-15

## What it turned out to be

We described ourselves to the carrier two different ways in the same call:

    Contact: <sip:192.168.100.59:5060>     SIP: we are at a private address
    c=IN IP4 49.244.163.169                SDP: send media to a public one

`external_signaling_address` and `external_media_address` were both set to the
detected public address, but PJSIP had already rewritten the Contact to the
private address. NTC's IMS answers that contradiction by establishing the call
and sending **no RTP whatsoever** — roughly 300 packets out per call, zero
back, while SIP continues normally in both directions.

The fix is to advertise neither address and let the carrier latch onto the
source address our packets actually arrive from, which is exactly what a
softphone does:

    ;external_media_address
    ;external_signaling_address
    local_net = 192.168.100.0/24

This is `SIP_NAT_MODE=latch` in `asterisk/bin/entrypoint.sh`, and it is the
default. It depends on three things that are all true here and must be
rechecked elsewhere: `rtp_symmetric` and `force_rport` on the endpoint (both
on), and a NAT that preserves UDP source ports (`scripts/stun_probe.py`).

First working call after the change:

    recorded 9120 bytes (1.1s)
    stt: 'Hello.'
    llm: "Hey there! How's your day going?"

## The one fault that was real, and separate

Before any of the media work: the host had moved to a different connection and
`secrets/sip_trunk.env` still pinned the old values.

| Value | Was | Actually |
|---|---|---|
| `SIP_EXTERNAL_IP` | `103.129.134.143` | `49.244.163.169` |
| `SIP_LOCAL_NET` | `192.168.1.0/24` | `192.168.100.0/24` |

This fails in a way that hides itself. Registration is an *outbound* request:
it creates a NAT mapping on the way out and the carrier's 200 OK returns
through it, so the trunk reports `Registered` no matter what address we claim.
Inbound is the opposite — the carrier takes the registered address and sends
the INVITE there on its own. With a stale address the INVITE goes to whoever
holds it now, and the carrier tells the caller **"the number you have dialed
is not registered"** while our side still says `Registered`. Both are true.

Fixed, and made self-correcting: `make asterisk-up` now detects the public
address over HTTPS and the LAN subnet from the host's own link routes, and
passes both to the container, where a detected value overrides the secret file
and warns on a mismatch. The values in `secrets/sip_trunk.env` are a fallback
for when detection fails, not the source of truth.

Fixing this made calls connect and the greeting play. It did not fix media.

## What we thought it was, and why each was wrong

Every one of these was believed, acted on, and disproven. They are recorded
because the wrong turns are most of the cost of this kind of fault, and
because two of them are still plausible-sounding enough to be tried again.

**The carrier was at fault.** The reasoning: our SDP named the correct public
address and port, the NAT preserved ports, ~200 outbound packets per call held
the pinhole open, the host firewall was off, and still nothing came back —
therefore the problem must be upstream at NTC. Disproven by a single fact from
the user: a softphone gets two-way audio on this same connection and this same
account. If the carrier could not deliver media here, it could not deliver it
to the softphone either. **This was the most expensive wrong turn**, because
it stopped the search: twice it was written up as "a question for the carrier,
not a setting."

**`local_net` was wrong or harmful.** The reasoning: a softphone has no such
setting, and the private address was leaking into headers somehow. Cleared it
and restarted. No change. `local_net` only suppresses NAT rewriting for
destinations inside it, and the carrier is outside it.

**`stunaddr` was poisoning the SDP.** The reasoning looked airtight: a capture
showed the SDP advertising `m=audio 20004` while RTP left from port 20014, so
Asterisk appeared to be announcing a port it was not using — which is exactly
the first occurrence's failure mode. Disabled `stunaddr`; no change.

The reasoning was airtight and the measurement was not. **Those two numbers
came from two different calls.** They were never supposed to match. Captured
properly, within a single call, the ports always agreed:

    SDP:  m=audio 20012
    RTP:  192.168.100.59:20012 > 202.70.74.178:16696

`stunaddr` was restored. The lesson is narrow and worth keeping: a port in a
packet capture and a port in a SIP trace are only comparable when they carry
the same call id.

**The host firewall was dropping inbound RTP.** `systemctl is-active` appeared
to report ufw as active, which fit the symptom — everything correct on the
wire, nothing arriving. `sudo ufw status verbose` said `Status: inactive`. The
earlier reading was of a different unit. It would not have explained the
captures in any case: tcpdump sits below netfilter, so a firewall drop still
appears in a capture, and nothing did.

**A softphone was stealing the binding.** Discovered partway through, and real
but not the cause: NTC's IMS keeps **one binding per account**. Whichever
client registered last owns inbound calls and the other does not ring at all.
With a softphone registered, a test call reached it and Asterisk saw no INVITE
whatsoever — the caller heard "busy" and the softphone logged a missed call.

This matters for any future comparison: a softphone left registered silently
takes every inbound call from Asterisk, while Asterisk keeps reporting
`Registered`. It was tested as an explanation for the rewritten Contact and
ruled out — force-stopped, with Asterisk the sole registrant, the IMS still
returned the private address and the next call still recorded 0 bytes.

**The IMS was rewriting our Contact against us.** The observation was correct:

    we send:    Contact: <sip:+97760410099@49.244.163.169:5060;line=bibyiig>
    IMS stores: Contact: <sip:+97760410099@192.168.100.59:5060;line=bibyiig>

and every inbound INVITE was then addressed to `192.168.100.59`. The wrong
part was the conclusion — that this was the carrier's choice and unfixable
from here. It was the symptom of our own contradiction. Once we stopped
claiming a public address the IMS had no reason to override, the same stored
private address worked fine, because the carrier latches rather than routing
to the literal value.

## What actually found it

Comparing our REGISTER, header by header, against how a working softphone
behaves on the same network and account. The difference was visible
immediately: we put a public address in Via and Contact; a softphone puts its
private address there and lets `rport`/`received` do the work.

That comparison was proposed early and deferred repeatedly in favour of
reasoning about what *should* work. It was the user's insistence on returning
to it — "check against zoiper, it should have worked" — that produced the fix.

Note that the passive capture never happened and was not needed: the softphone
ran on a phone, whose traffic reaches the router without crossing this host.
Knowing *how a softphone behaves* was enough; capturing its packets was not
required.

## How to debug this class of fault

In the order that would have been fastest, which is not the order it happened.

1. **Is the call even arriving?** `ari show apps` must list `pana-voice`, and
   the dialplan must reach `Stasis`. A whistle instead of Pana means the
   dialplan worked and the voice service was not subscribed — a running
   process is not a subscribed one.
2. **Does the NAT preserve ports?** `python3 scripts/stun_probe.py`. This
   chooses which half of this document applies.
3. **Which direction is missing?** Capture on the physical interface:
   `tcpdump -ni wlp3s0 'udp and host <carrier>'`. Count each way. Hundreds out
   and zero in is this fault.
4. **Do SIP and SDP agree about where we are?** Turn on `pjsip set logger on`
   and read the `Contact:` and `c=IN IP4` of **one** call together. If one is
   private and the other public, that is the bug, and `SIP_NAT_MODE=latch` is
   the fix.
5. **Only then** consider the carrier.

Two traps worth naming. Never compare values taken from different calls.
And `pjsip send register` sends `Expires: 0` first, which de-registers the
trunk — turn the logger on and wait for the natural refresh instead.

---

# The first occurrence

Kept in full. This analysis applies to a NAT that rewrites RTP source ports,
which `scripts/stun_probe.py` will tell you about in one command. It did not
apply to the second occurrence, and reading it as though it did is what
misdirected that search.

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

**A stale public address.** This *was* a real fault and is fixed -- and it
recurred on the next move, which is why detection is now automatic; see "The
one fault that was real, and separate" above. The external
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

That last sentence is true of the NAT described here and not of NATs in
general. On a port-preserving NAT those same three settings are exactly what
makes inbound audio work -- see the second occurrence above.

## What is still in the tree from this work

Kept because it is correct on a host with a public address, and inert here:

- `stunaddr` and `rtpkeepalive` in `asterisk/rtp.conf`
- `SIP_MEDIA_VIA_STUN` in `asterisk/bin/entrypoint.sh` and
  `docker-compose.asterisk.yml`, default `false`. Setting it `true` drops
  `external_media_address` while keeping the signalling one. It has no effect
  under `SIP_NAT_MODE=latch`, which drops both.
- `VOICE_KEEP_RECORDINGS` -- keeps each turn's recording instead of deleting
  it and logs its size. Zero bytes distinguishes a media path problem from a
  recognition one in one line of log. Off by default; these are recordings of
  real conversations.
- `scripts/rtp_probe.py` -- the isolation test. Run it before assuming any
  future audio fault is in the pipeline.

## What would fix it

This section is about the port-rewriting NAT above. It is not the remedy for
the 2026-10-15 fault, which needed no new hardware at all.

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
