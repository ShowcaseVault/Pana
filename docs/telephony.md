# Telephony

Asterisk holds a SIP trunk to the carrier. It is the only component that ever
sees the trunk password; the FastAPI application and the Celery workers do not,
and must not be given it.

This document covers the trunk itself: where the credentials live, why they
live there, and how to prove the trunk works. The AI conversation that will run
over these calls is a separate layer, sketched at the end.

## Why the credentials are handled the way they are

SIP trunk credentials authorise outbound calls billed to our carrier account.
Anyone holding them can place calls at our expense, and carriers do not refund
fraudulent traffic. Automated scanners sweep the public internet for SIP ports
continuously, so an exposed or misconfigured PBX is usually found in hours, not
months. That threat shapes every choice below.

**Not in the database.** The database is the largest breach surface in the
system: injection, backups, replicas, and a dump on someone's laptop all reach
it. Encrypting the credentials in a column does not help much either, because
the decryption key then has to live somewhere the application can read it,
which is the problem we started with, plus a moving part.

**Not in `.env`.** `.env` is read by the API and the workers. Neither places
calls, so neither needs the password, and a template-injection or file-read bug
in the API should not be able to reach it.

**In a file only Asterisk can read.** `secrets/sip_trunk.env` is git-ignored,
mounted read-only into the container, and rendered at start into
`/etc/asterisk/pjsip.conf` as mode `600` owned by `asterisk`. The entrypoint
refuses to start if the secret file is readable by group or other, and unsets
the password from its environment before executing Asterisk, so it does not
appear in `/proc/<pid>/environ` for the long-running process. `.dockerignore`
excludes `secrets/`, so no credential can reach an image layer or a registry.

## Setup

```
make asterisk-secret     # creates secrets/sip_trunk.env, mode 600
$EDITOR secrets/sip_trunk.env
make asterisk-up         # builds, detects IP and subnet, starts
make asterisk-check      # must end with: the trunk is registered
```

`make asterisk-up` is the only start command to use, on first setup and after
every network change. It rebuilds the image (a cache hit when nothing changed)
and detects the network each time, so there is nothing to edit by hand when
the host moves. Starting the container any other way -- `docker compose up`,
`docker start` -- skips both.

The carrier gives you five values, which map to the file as follows.

| Carrier's term | Variable | Notes |
|---|---|---|
| Username | `SIP_USERNAME` | Appears in the From and Contact user part |
| Password | `SIP_PASSWORD` | Treat as a live payment credential |
| Auth name | `SIP_AUTH_NAME` | Set equal to `SIP_USERNAME` if not issued separately |
| Domain | `SIP_DOMAIN` | Host only, no `sip:` and no scheme |
| Outbound proxy | `SIP_OUTBOUND_PROXY` | `host` or `host:port` |

Set `SIP_TRANSPORT=tls` if the carrier supports it. With `udp` or `tcp` the
authentication exchange crosses the network in the clear.

Leave `SIP_EXTERNAL_IP` and `SIP_LOCAL_NET` empty in the secret file. Both
values go stale as soon as the host moves to a different connection, and
a stale one fails in a way that hides itself: registration is an outbound
request the carrier answers over the same flow, so the trunk still reports
`Registered` while every inbound INVITE is routed to an address that is not
ours. `make asterisk-up` therefore detects both at start -- the public address
over HTTPS, the subnet from the host's own link routes -- and passes them to
the container, where a detected value wins over the one in the secret file.
The secret file's values are the fallback for when detection fails, not the
source of truth.

`SIP_NAT_MODE` decides what, if anything, Asterisk advertises as its external
address. It defaults to `latch`, which is what the NTC trunk needs.

| Mode | Advertises | For |
|---|---|---|
| `latch` (default) | neither address | a carrier that latches onto our source address |
| unset | `external_media_address` and `external_signaling_address` | a host whose public address the far end must be told |
| unset + `SIP_MEDIA_VIA_STUN=true` | signalling only; media from `stunaddr` | a NAT that rewrites RTP ports |

Under `latch`, Asterisk describes itself by its private address everywhere,
exactly as a softphone does, and the carrier replies to wherever our packets
came from. It needs `rtp_symmetric` and `force_rport` on the endpoint (both
on). `SIP_EXTERNAL_IP` is then unused for the transport, though it stays
detected and available for the other modes. `latch` has carried two-way calls
on every connection tried so far, including ones whose NAT rewrites ports.

Do not pin the media address on this carrier. Claiming a public address in the
SDP while the SIP headers say we are private is a contradiction, and NTC's IMS
answers it by sending no media at all: the call connects, the caller hears
Pana, and Pana hears nothing. See
[telephony-incidents.md](telephony-incidents.md#2-ims-sends-no-audio).

## Testing the trunk

Registration proves only that the carrier accepted our credentials. It says
nothing about whether calls work, so test each direction separately.

### Outbound first

Outbound needs no port forwarding: our registration keeps a path open through
the router, and we initiate the call. Test it before touching the firewall.

```
make asterisk-call NUMBER=9812345678
```

The phone should ring and play a prompt when answered. That single test
covers signalling, authentication, codec negotiation, and NAT traversal.

NTC takes the national number (`98XXXXXXXX`). If every number, in every format,
comes back as `183` carrying `Reason: Q.850;cause=1;text="Unallocated
(unassigned) number"`, the number is not the problem: the Request-URI is. It
must name the domain (`INVITE sip:98XXXXXXXX@ims.ntc.net.np`) and reach the
proxy through `outbound_proxy`. With the proxy's IP in the Request-URI
(`INVITE sip:98XXXXXXXX@202.70.74.178`) the IMS rejects every call this way.
The endpoint and AOR in `pjsip.conf.template` are set up for the first form.

A test call from `asterisk-call` shows as a private number on the phone: a CLI
originate has no caller ID, so Asterisk sends `"Anonymous"`. Calls placed
through the dialplan or ARI carry the endpoint's `callerid`.

### Then inbound

Ring the DID (`SIP_USERNAME`) from any phone while watching:

```
make asterisk-watch
```

A working inbound call prints `Inbound call from ... to ...` and answers. With
`make voice` running, Pana greets the caller; without it, the caller hears
`cid_whistle`. Either one proves signalling, codec negotiation, and RTP work.

Prompts are baked into the image, so changing one means a rebuild -- see
[../asterisk/sounds/README.md](../asterisk/sounds/README.md). Asterisk cannot
play mp3; audio must be converted to 8 kHz mono WAV first.

No port forwarding is needed. NTC delivers inbound calls over the path our
registration opened, and that has worked from home connections behind NAT and
CGNAT. If a call never arrives, use the runbook under
[When callers hear "not registered"](#when-callers-hear-not-registered) before
touching the router.

### Is the call even reaching us?

This is the question worth answering first, because it splits the problem in
two and the two halves have nothing in common.

```
make asterisk-diagnose
```

Run it, ring the DID, and it watches three layers at once:

- **packets** -- did an INVITE arrive on UDP 5060 at all
- **SIP** -- what Asterisk made of it, and what it replied
- **dialplan** -- did the call reach `from-carrier` and get accepted

**No INVITE arrived.** The carrier did not send the call to us. Work through
the [runbook](#when-callers-hear-not-registered): a stale image, another
client registered on the account, and NTC-side state have each been the
cause. NAT and CGNAT have not.

**An INVITE arrived but the call failed.** Now it is ours, and the SIP trace
shows the response code we sent back. `404` from us means the dialplan found no
matching extension -- usually the carrier delivers the DID in a different form
than `CARRIER_DID`, which the `Rejecting call to ...` log line will show.

For a snapshot with no call involved:

```
make asterisk-status
```

Registration state, live channels, the limits in force, and how many inbound
calls have arrived and been rejected since start. `arrived: 0` after ringing
the DID means the call is not reaching the dialplan, which points back to
`make asterisk-diagnose`.

### Reading a failure

| What you see | Means |
|---|---|
| 401 / 407 | authentication; unexpected when registration is up |
| 403 | the carrier refused the call: number format, or the trunk is barred for that destination |
| 404, or `183` with `cause=1` "Unallocated number" | the number, or the Request-URI naming the proxy IP -- see "Outbound first" |
| 488 | codec mismatch; the carrier wants something other than ulaw/alaw |
| call connects, Pana hears nothing | SIP and SDP disagree about our address; keep `SIP_NAT_MODE=latch` |
| audio one way | RTP blocked in one direction |
| nothing in the trace at all | the INVITE never reached us |

`make asterisk-watch` and the test script both enable `pjsip set logger on`,
which prints full SIP messages including the `Authorization` header. Turn it
off with `pjsip set logger off`, and strip that header before sharing a trace.

## The firewall is the other half

The container uses host networking, so the host's firewall is what stands
between the carrier's port and the internet. Nothing in this repository opens
that port for you, and it should not be open to the world.

Allow SIP and RTP only from the carrier's signalling addresses. Ask the carrier
for them; do not infer them from a DNS lookup, which can change.

```
# Replace 198.51.100.0/24 with the carrier's actual range.
sudo ufw allow from 198.51.100.0/24 to any port 5060 proto udp
sudo ufw allow from 198.51.100.0/24 to any port 20000:20099 proto udp
```

ARI listens on `127.0.0.1:8088` and must stay there. It can originate calls,
so exposing it is equivalent to exposing the trunk credentials.

## What limits the damage if the credentials leak anyway

Two ceilings, both set in `.env` (not in `secrets/sip_trunk.env`, which holds
only the credentials) and applied at container start:

| Variable | Default | Bounds |
|---|---|---|
| `SIP_MAX_CHANNELS` | `2` | calls at once on the trunk |
| `SIP_MAX_CALL_SECONDS` | `180` | length of any single call |

`SIP_MAX_CHANNELS` becomes `device_state_busy_at` on the endpoint: even with
valid credentials, nobody can place more calls at once than this.

`SIP_MAX_CALL_SECONDS` becomes `TIMEOUT(absolute)` on every answered call, in
both directions. It bounds two different costs: carrier minutes on a billable
call, and the channel plus media session held open on our side. A call still up
at the limit is hung up. The entrypoint refuses to start on a non-numeric value
or anything under 10 seconds, since that would cut off calls before they are
usable.

Both take effect when the container is recreated, not merely restarted:

    make asterisk-down && make asterisk-up

### Answering is what costs money

Inbound calls are screened before `Answer()`, not after. A call to anything
other than our DID is hung up while still ringing, which is free; answering is
what starts billing and what commits a channel. This matters most if UDP 5060
is ever reachable beyond the carrier, where an auto-answering dialplan turns
scanner traffic into charges.

Whether inbound is billable at all is the carrier's policy, not ours. Most
charge the caller only, but some charge inbound termination per minute, and a
mobile IMS subscription is not always billed like a wholesale SIP trunk. Ask
the carrier, or measure it: note the balance, take one short call, check again.

Ask the carrier to add, on their side: a spending cap, a concurrent-channel
limit, and a geographic allowlist for destinations you actually call.
Provider-side limits keep working when ours have been bypassed.

Anonymous inbound calls are rejected by construction: the only `identify`
section matches the carrier, so traffic from anywhere else matches no endpoint.
Do not add an endpoint named `anonymous`; it would undo this.

## If the credentials are exposed

Rotate first, investigate second.

1. `make asterisk-down`.
2. Ask the carrier to reset the trunk password and to check recent call
   detail records for traffic you do not recognise.
3. Put the new password in `secrets/sip_trunk.env`, then `make asterisk-up`.
4. If the old value ever reached git, rotating is the fix. Rewriting history
   is not, because clones and forks keep the old objects.

## Layout

```
asterisk/
  Dockerfile              Ubuntu 22.04 base; Debian dropped the package
  asterisk.conf           runs as the asterisk user; multiarch module path
  modules.conf            autoload with a noload list; chan_sip is refused
  extensions.conf         dialplan (from-carrier, to-carrier)
  http.conf               ARI bound to 127.0.0.1 only
  rtp.conf                RTP port range
  logger.conf             logs to stdout
  ari.conf.template       rendered with a generated password
  templates/
    pjsip.conf.template   rendered with the carrier credentials
  sounds/                 prompts, copied to sounds/en/pana/ at build time
  bin/
    entrypoint.sh         renders config, then execs Asterisk
    smoke-test.sh         proves the trunk is registered
secrets/
  sip_trunk.env.example   copy to sip_trunk.env and fill in
  sip_trunk.env           git-ignored, mode 600, never in an image
```

## Troubleshooting

Read the registration state first; it distinguishes a credential problem from
a network problem.

```
make asterisk-cli
  pjsip show registrations
  pjsip show contacts
  pjsip set logger on      # full SIP trace, includes headers
```

| Symptom | Usual cause |
|---|---|
| `Rejected` / 403 Forbidden | `SIP_AUTH_NAME` or `SIP_PASSWORD` wrong |
| `Registered` but no inbound calls | carrier not routing the DID yet, or the `identify` match misses their proxy |
| Carrier says "the number you have dialed is not registered" | work through [the runbook below](#when-callers-hear-not-registered) in order |
| Every outbound call: `183` with `cause=1` "Unallocated number" | Request-URI names the proxy IP instead of the domain -- see "Outbound first" |
| Caller hears a whistle instead of Pana | the dialplan ran but the voice service was not subscribed to ARI; `ari show apps` is empty |
| Call connects, caller hears Pana, Pana hears nothing | SDP and SIP disagree about our address; use `SIP_NAT_MODE=latch` |
| A config change has no effect | the container runs a stale image; start it with `make asterisk-up`, which builds |
| Call connects, no audio either way | NAT: check the RTP range is open |
| Audio one way only | RTP blocked in one direction by the firewall |
| No registration attempt at all | outbound 5060 blocked, or `SIP_OUTBOUND_PROXY` unreachable |
| `No such command 'pjsip show ...'` | the pjsip stack did not load; check `docker logs` for "declined to load" and see the note below |

Asterisk resolves module dependencies internally, and that graph is not visible
in any config file. With `autoload = no`, one missing entry makes a module and
everything downstream of it decline to load -- so omitting `res_sorcery_config`
takes out the entire SIP stack while Asterisk still starts and reports healthy.
`modules.conf` therefore uses `autoload = yes` with an explicit `noload` list.
Some modules decline on every start (voicemail, queues, CDR backends, SNMP);
they need config files we do not ship and are not used here.

`pjsip set logger on` prints full SIP messages including the `Authorization`
header. Do not paste that output into a ticket or a chat without removing it.

Do not use `pjsip send register` to inspect a registration. It sends
`Expires: 0` first, which de-registers the trunk with the carrier -- inbound
calls fail for as long as it takes Asterisk to register again. Turn the logger
on and wait for the refresh (`SIP_REGISTRATION_EXPIRY`, 120s by default)
instead.

### The whistle means the dialplan worked

`Playback(pana/cid_whistle)` in `from-carrier` is the fallback for
`STASISSTATUS != SUCCESS`. Hearing it is good news about everything below the
application: the carrier routed the DID, the INVITE arrived, `identify` matched
it, the dialplan accepted the extension and answered. Only the handover to the
voice service failed, and Asterisk says so directly:

    ERROR res_stasis.c: stasis_app_exec: Stasis app 'pana-voice' not registered

Confirm with `ari show apps` -- an empty list means nothing is subscribed.
A running process is not the same as a subscribed one: if the service was
killed, its ARI WebSocket is gone while a stale process may still match
`pgrep`. Check the subscription, not the process list.

## Moving the host to a different connection

Nothing to edit. On the new network:

```
make asterisk-up       # rebuilds, detects and prints public IP and LAN
make voice             # in another terminal; restart it after every asterisk-up
docker exec asterisk-pana asterisk -rx 'pjsip show registrations'   # Registered
docker exec asterisk-pana asterisk -rx 'ari show apps'              # pana-voice
```

Then call the DID. The public IP and the LAN subnet both change with the
network, and a stale value fails in a way that hides itself (see
[incident 1](telephony-incidents.md#1-stale-public-address)), which is why
both are detected on every start rather than configured.

## When callers hear "not registered"

`pjsip show registrations` says `Registered`, and callers hear NTC's recording
"the number you have dialed is not registered". Registration succeeding proves
almost nothing here: it is outbound, and the 200 OK comes back over the flow
the REGISTER opened, whatever is wrong. Work through these in order. Each step
is cheap, and the first ones are the ones that have actually been the cause.

1. **Start with `make asterisk-up`, never anything else.** It rebuilds the
   image and detects the network. On 2026-10-29 the container was still
   running an image built on 2026-09-20, so a month of entrypoint fixes had
   never run on that machine. Check with
   `docker exec asterisk-pana md5sum /usr/local/bin/entrypoint.sh` against
   `md5sum asterisk/bin/entrypoint.sh`: different sums mean a stale image.
2. **Check the detected values.** `make asterisk-up` prints the public address
   and local network; they must match the network the host is on now.
3. **Nothing else registered on the account.** NTC keeps one binding per
   account and gives inbound calls to it. A softphone left registered with the
   same credentials takes every call while Asterisk still says `Registered`.
   Force-stop it, then wait for Asterisk's next REGISTER (up to two minutes).
4. **Does the INVITE reach us?** Turn on `pjsip set logger on`, call, and look
   for `INVITE sip:+977...`. A carrier `NOTIFY` (`Event: ua-profile`) arrives
   after every REGISTER; seeing it means the path from the carrier to us
   works, so if NOTIFYs arrive and the INVITE does not, the IMS chose not to
   deliver the call. Nothing in our network is blocking it.
5. **If 1-4 are clean and the INVITE still never arrives: reset the IMS side
   with a softphone.** Register Zoiper on the same account, make a call in each
   direction, force-stop it, wait two minutes for Asterisk to re-register, and
   call again. This is what brought inbound back on 2026-10-29. Exactly what
   it resets on NTC's side was not isolated, but it is the step that turned
   the same configuration from failing to working.

What each of these fixed, and the long list of things that were tested and
ruled out (NAT port rewriting, CGNAT, NAT modes, keepalive, ports, "needs a
VPS"), is in [telephony-incidents.md](telephony-incidents.md). Read the
ruled-out table before trying anything not on this list.

## When Pana cannot hear the caller

The call connects and the caller hears Pana, but every turn logs `recorded 0
bytes` and Pana says it could not hear. Inbound audio is not arriving.

1. Keep `SIP_NAT_MODE=latch` (the default). Advertising a public address in
   SDP while SIP says we are private makes NTC send no audio at all
   ([incident 2](telephony-incidents.md#2-ims-sends-no-audio)).
2. Turn on `VOICE_KEEP_RECORDINGS=true` to see the byte count on every turn.
   Zero means a media-path fault; a non-zero count with a wrong transcript
   points at recognition instead. Turn it off afterwards, since it keeps
   recordings of real conversations.
3. `scripts/rtp_probe.py` answers one call and records ten seconds through ARI
   alone, with no recognition, synthesis or turn loop. Zero bytes places the
   fault below the application.
4. In one call's trace (`pjsip set logger on`), read the `Contact:` and the
   SDP `c=IN IP4` together. Both must be the private address under `latch`.
   Compare values only within one Call-ID.

## The AI conversation

`from-carrier` hands an answered call to `Stasis(pana-voice)`, the app served
by `voice_service/`. That call blocks for the length of the conversation, and
the service hangs up when it is finished.

`Stasis` returning is therefore not by itself a failure, which is why the
fallback is gated on `STASISSTATUS` rather than on reaching the next line:

- `SUCCESS` -- the app ran and the call is over. Nothing more to play; the
  dialplan jumps straight to `Hangup`. Without this test the caller would hear
  the fallback prompt tacked onto the end of every successful conversation.
- anything else -- the app was never there (no service running, or an app name
  that does not match `ARI_APP_NAME`). The caller is on an answered, billable
  line hearing silence, so the fallback prompt plays and the call ends.

    voice_service/
      app.py           Stasis event loop and the per-call turn loop
      ari.py           ARI client -- events websocket plus the REST calls used
      pipeline.py      stt / llm / tts, the three seams
      providers/       Groq for stt and llm, NVIDIA Magpie for tts
      audio.py         u-law and resampling between trunk and models

Run it with `make voice`, alongside `make asterisk-up`. Both read
`ARI_PASSWORD` from `.env`: Asterisk renders it into `ari.conf` at start, the
voice service authenticates with it. Neither invents a default, so a missing
value fails at start on both sides rather than half-working. Generate one with:

    openssl rand -hex 32

### Turn taking, and what replaces it

Today a turn is record-then-respond: `record` on the channel with
`maxSilenceSeconds` ending the turn, then download the recording, run it
through the pipeline, and play the reply. This needs nothing beyond ARI itself,
which is why it is the first version.

The end state is an `externalMedia` channel bridged to the caller, forking call
audio as RTP. That is what makes barge-in possible: audio flows continuously
rather than in turns, so the caller can interrupt. The codec choice in
`pjsip.conf` (`ulaw` first) already matches what the realtime speech APIs
expect, so no transcode is needed. The `stt`/`llm`/`tts` signatures do not
change when that swap happens.

### Speech and generation

Three stages, all hosted:

| Stage | Provider | Model setting |
|---|---|---|
| `stt` | Groq | `STT_MODEL_REALTIME` |
| `llm` | Groq | `LLM_MODEL_REALTIME` |
| `tts` | NVIDIA Magpie | `TTS_VOICE` |

There is no offline path. Vosk and Piper were here while the providers were
undecided, and were removed once they were: ~200 MB of models and packages
standing in for services that are now configured. A stage that fails logs it
and the turn ends short; the loop continues, so one bad turn does not end the
call. A local recogniser that mishears the caller is not a better call than a
short apology.

Groq answers and Groq transcribes, so a call needs one key (`GROQ_API_KEY`)
rather than two. Both stages have a `_REALTIME` model setting separate from the
batch one, so a call can move to a faster model without touching diary
generation. A call is latency-bound, not accuracy-bound: a better transcript
that lands a second later is a worse call. The reply is capped at
`LLM_MAX_TOKENS` on the model rather than trimmed afterwards, so nothing is
generated and then thrown away.

Magpie runs two ways behind one client. The default is NVIDIA's hosted build on
Cloud Functions, which wants `TTS_FUNCTION_ID` as call metadata over TLS plus
`NVIDIA_API_KEY`; a self-hosted NIM (`docker-compose.magpie.yml`, needs a GPU)
is a plain gRPC target with neither. Pointing `TTS_URI` at the local NIM,
clearing `TTS_FUNCTION_ID` and setting `TTS_USE_SSL=false` is the whole switch.
`scripts/test_magpie_tts.py` exercises the endpoint on its own, outside a call.
22.05 kHz is asked for rather than 44.1: it is already past what a phone line
carries, at half the bytes per chunk.

`riva-client` is synchronous gRPC, so its stream is consumed on a worker thread
and handed back over a bounded queue. Iterating it on the event loop would
block every other call on the service for the length of the synthesis.

That handoff uses a thread-native queue and a stop flag, not an `asyncio`
queue. The consumer routinely abandons the stream mid-reply -- the caller hung
up -- and a producer parked on a full `asyncio.Queue` can only be released by
the event loop, which the abandoned generator never gets back to. The thread
would sit there for the life of the process, and enough hangups exhaust the
executor pool and stop synthesis entirely. With a stop flag the producer
notices, drops the gRPC stream so the rest is never synthesised or billed, and
unwinds.

Resampling carries its state between chunks. 22.05 kHz to 8 kHz is a ratio of
2.75625, so every chunk boundary falls mid-sample; resampling each chunk from a
standing start loses that fraction and clicks at every join.

### What Pana is on the call

A companion, not an assistant: someone who listens and also takes a turn of
their own. Most of that is the prompt (`prompts/voice_companion.py`, wired in
as `VOICE_LLM_PROMPT`) -- react honestly, say what you think, pick a thread
back up, ask a question only when you want the answer, never two in a row.

The rest is turn-taking here, which has to agree with it. A `maxSilenceSeconds`
of 2 and a 15-second ceiling are assistant numbers: they cut someone off in the
pause in the middle of a hard sentence. A turn runs to 45 seconds and ends on
3 seconds of silence instead.

A turn longer than `BACKCHANNEL_OVER_SECONDS` that does not end in a question
gets a short "Mm." or "Go on." rather than a considered reply -- the caller is
mid-flow, and an insight there is an interruption. What they said still goes
into the history, so the next real reply answers all of it. Length is measured
on the audio, minus the trailing silence Asterisk waits through, not on the
transcript: it is how long they held the floor that matters.

### Chunked turns

A turn is not processed as one block. The model streams its reply and
`llm_stream` yields it a **sentence** at a time; each sentence is synthesised
while the previous one is still playing. The caller hears the first words in
about the time that first sentence takes, rather than waiting for generation
plus synthesis of the whole answer.

Sentences, not tokens, are the unit. A synthesiser needs a complete clause to
get the prosody right -- handing Magpie three words at a time produces speech
that sounds chopped even though the audio itself is continuous. A sentence
shorter than `MIN_CHUNK_CHARS` waits and is spoken with the next one, so an
abbreviation does not become its own utterance.

Playback stays sequential: Asterisk plays one file per sentence, in order, and
the turn loop waits for each `PlaybackFinished`. The chunking buys time to
first word, not overlapping audio. A synthesis failure partway through a reply
ends it there rather than restarting and repeating half a sentence.

Each wait is keyed on the operation it belongs to -- the id ARI returns for a
playback, the name we chose for a recording -- rather than on one event per
kind. A shared event is wrong as soon as a reply is several playbacks long: a
late or duplicate `PlaybackFinished` for one sentence releases the wait
belonging to the next, and the caller hears it cut off. Waiters are registered
before the operation starts where the key is known in advance, because
Asterisk can report a short recording finished before the code that started it
is back to waiting on it.

Only what the caller actually heard goes into the history. A reply cut short by
a hangup is remembered as far as it was played and no further, so the next turn
never answers a sentence that never reached them.

Three consecutive turns that transcribe to nothing end the call, after saying
so. A bad line or an open mic would otherwise re-prompt until the dialplan's
own timeout, billing the whole way.

The service keeps the last `HISTORY_TURNS` turns as context -- enough to pick
up something said several minutes earlier, which is most of what makes it feel
like one conversation rather than a series of exchanges. A turn that
transcribes to nothing is not added to it: the caller is re-prompted instead,
so the model never has to interpret an empty message.

### Playing generated audio

Asterisk plays from a file by path, never from bytes. A turn's reply is written
to `var/voice/` on the host, which is bind-mounted to `/var/spool/pana-tts` in
the container, and played as `sound:/var/spool/pana-tts/<name>` -- a `sound:`
URI takes the path without its extension. The file is `.ulaw`: headerless, read
by extension, already at the trunk's rate, so playback does not transcode. Each
file is deleted once played.

That directory is deliberately outside `/var/lib/asterisk`, which has a named
volume mounted over it.
