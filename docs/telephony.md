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
make asterisk-build
make asterisk-up
make asterisk-check      # must end with: the trunk is registered
```

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

If the host is behind NAT, set `SIP_EXTERNAL_IP` to its public address and
`SIP_LOCAL_NET` to the private subnet. Leaving `SIP_EXTERNAL_IP` empty on a
NATed host is the usual cause of a call that connects with no audio.

## Testing the trunk

Registration proves only that the carrier accepted our credentials. It says
nothing about whether calls work, so test each direction separately.

### Outbound first

Outbound needs no port forwarding: our registration keeps a path open through
the router, and we initiate the call. Test it before touching the firewall.

```
make asterisk-call NUMBER=9779812345678
```

The phone should ring and play `cid_whistle` when answered. That single test
covers signalling, authentication, codec negotiation, and NAT traversal.

The number format is the carrier's, not ours. NTC generally wants the full
national number without a leading `+`; if the carrier returns 404, try it with
and without the country code before assuming the trunk is broken.

### Then inbound

Ring the DID (`SIP_USERNAME`) from any phone while watching:

```
make asterisk-watch
```

A working inbound call prints `Inbound call from ... to ...`, then answers and
plays `cid_whistle`. Hearing that whistle end to end is the proof that
signalling, codec negotiation, and RTP all work.

Prompts are baked into the image, so changing one means a rebuild -- see
[../asterisk/sounds/README.md](../asterisk/sounds/README.md). Asterisk cannot
play mp3; audio must be converted to 8 kHz mono WAV first. Nothing at all in the trace means the INVITE never arrived,
which is a firewall or NAT problem, not an Asterisk one.

Inbound is the harder direction behind NAT. The registration holds a pinhole
open at the router, and many carriers reuse it, in which case inbound works
with no port forwarding at all. If it does not, forward UDP 5060 and the RTP
range to this host -- and read the firewall section below first, because a
forwarded 5060 is reachable by anyone, not only the carrier.

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

**No INVITE arrived.** The call never reached this host, so no Asterisk setting
is the cause. The likely reasons, in order: the carrier is not routing the DID
to this trunk; the router is not forwarding UDP 5060 and the carrier is not
reusing the registration pinhole; a host firewall is dropping it; or the ISP
uses CGNAT, where inbound forwarding is impossible and the registration path is
the only one available.

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
| 404 | the carrier did not recognise the number |
| 488 | codec mismatch; the carrier wants something other than ulaw/alaw |
| call connects, silence | NAT: `SIP_EXTERNAL_IP` wrong, or RTP not forwarded |
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
| Call connects, no audio | NAT: set `SIP_EXTERNAL_IP`, and check the RTP range is open |
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
