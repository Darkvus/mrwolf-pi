FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git wget subversion libjansson-dev libxml2-dev \
    libsqlite3-dev uuid-dev libssl-dev bluez libbluetooth-dev \
    libsrtp2-dev libedit-dev pkg-config ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Compila Asterisk (LTS) con soporte para módulos externos (chan_mobile)
ARG ASTERISK_VERSION=20
RUN wget -q https://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_VERSION}-current.tar.gz -O /tmp/asterisk.tar.gz && \
    mkdir -p /usr/src/asterisk && tar -xzf /tmp/asterisk.tar.gz -C /usr/src/asterisk --strip-components=1 && \
    cd /usr/src/asterisk && \
    contrib/scripts/install_prereq install && \
    ./configure --with-bluetooth && \
    make menuselect.makeopts && \
    menuselect/menuselect --enable chan_mobile --enable res_pjsip --enable chan_pjsip menuselect.makeopts && \
    make -j$(nproc) && make install && make samples && make config

EXPOSE 8088 5038 5060/udp
CMD ["asterisk", "-f", "-vvv"]
