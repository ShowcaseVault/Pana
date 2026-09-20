# Asterisk with only the configuration this project needs. No credential is
# present in any layer of this image: pjsip.conf is rendered at container
# start from a mounted secret, and .dockerignore excludes secrets/ regardless.
#
# Ubuntu rather than Debian: Debian dropped the asterisk package after
# bullseye, so bookworm and trixie have no installation candidate. Ubuntu
# 22.04 carries Asterisk 18 (LTS), which has every module this setup loads.
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asterisk \
        asterisk-modules \
        gettext-base \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/* /etc/asterisk/*.conf

COPY asterisk.conf modules.conf extensions.conf http.conf rtp.conf logger.conf /etc/asterisk/
COPY templates/ /etc/asterisk/templates/
COPY ari.conf.template /etc/asterisk/templates/
# Custom prompts, played by the dialplan as pana/<name>.
COPY sounds/ /usr/share/asterisk/sounds/en/pana/

COPY bin/entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chown -R asterisk:asterisk /etc/asterisk /var/lib/asterisk /var/log/asterisk /var/spool/asterisk /usr/share/asterisk/sounds/en/pana

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
