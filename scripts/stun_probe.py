#!/usr/bin/env python3
"""Does the NAT in front of this host preserve UDP source ports?

That single property decides whether inbound audio can work from here at all.
Asterisk advertises its own RTP port in the SDP; if the NAT maps that port to
a different external one, the carrier sends audio to a port nothing is
listening on and the call is one-way. See docs/telephony-nat.md.

Run it with the Asterisk container stopped, or the ports are already in use:

    python3 scripts/stun_probe.py
"""

import os
import socket
import struct
import sys

# stun.l.google.com, as an IPv4 literal. A hostname resolves to AAAA first on
# some systems, and a STUN reply over IPv6 says nothing about the IPv4 mapping
# the carrier's audio has to traverse.
STUN_SERVER = ("74.125.250.129", 19302)

# Ports from the range in asterisk/rtp.conf, so the measurement describes the
# sockets Asterisk will actually use.
PORTS = (20000, 20001, 20002)

_MAGIC = 0x2112A442


def mapped_address(local_port, server=STUN_SERVER, timeout=4.0):
    """Return (ip, port) as the public side sees a socket bound to local_port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", local_port))
        sock.settimeout(timeout)
        # Binding request: type 0x0001, no attributes.
        sock.sendto(struct.pack(">HHI12s", 1, 0, _MAGIC, os.urandom(12)), server)
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            return None
    finally:
        sock.close()

    offset = 20  # past the STUN header
    while offset + 4 <= len(data):
        attr_type, length = struct.unpack(">HH", data[offset : offset + 4])
        value = data[offset + 4 : offset + 4 + length]
        # XOR-MAPPED-ADDRESS (0x0020), or MAPPED-ADDRESS (0x0001) from older
        # servers. The XOR form is obfuscated to survive NATs that rewrite
        # addresses they find in payloads.
        if attr_type in (0x0020, 0x0001) and len(value) >= 8:
            port = struct.unpack(">H", value[2:4])[0]
            addr = value[4:8]
            if attr_type == 0x0020:
                port ^= _MAGIC >> 16
                addr = bytes(a ^ b for a, b in zip(addr, struct.pack(">I", _MAGIC)))
            return socket.inet_ntoa(addr), port
        # Attributes are padded to a 4-byte boundary.
        offset += 4 + length + (-length % 4)
    return None


def main():
    results = []
    for port in PORTS:
        try:
            result = mapped_address(port)
        except OSError as exc:
            print(f"local :{port}  -> cannot bind ({exc})")
            print("Stop the Asterisk container first: make asterisk-down")
            return 2
        if result is None:
            print(f"local :{port}  -> no STUN reply")
            continue
        ip, mapped_port = result
        print(f"local :{port}  -> {ip}:{mapped_port}")
        results.append((port, mapped_port))

    if not results:
        print("\nNo STUN replies at all. Outbound UDP may be blocked.")
        return 2

    preserved = all(local == mapped for local, mapped in results)
    print()
    if preserved:
        print("Ports are PRESERVED. Inbound audio can work from this network:")
        print("keep SIP_MEDIA_VIA_STUN=false, so the SDP carries the static")
        print("external address and Asterisk's own (correctly mapped) port.")
    else:
        print("Ports are REWRITTEN. Asterisk advertises its internal port and")
        print("the carrier's audio is dropped. See docs/telephony-nat.md --")
        print("this needs a routable address or a tunnel, not a setting.")
    return 0 if preserved else 1


if __name__ == "__main__":
    sys.exit(main())
