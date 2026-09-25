# Build helper next to Show Network. Pin the upstream commit/tag for reproducibility.
ARG AVDECC_REF=dev
FROM debian:bookworm AS build
ARG AVDECC_REF
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake ninja-build git pkg-config libpcap-dev ca-certificates python3 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git clone --depth 1 --branch "$AVDECC_REF" https://github.com/L-Acoustics/avdecc.git
COPY collector.cpp /src/avdecc/examples/src/showNetworkCollector.cpp
COPY collector-cmake-snippet.txt /tmp/snippet.txt
RUN cat /tmp/snippet.txt >> /src/avdecc/examples/src/CMakeLists.txt \
 && cmake -S /src/avdecc -B /src/build -G Ninja \
      -DBUILD_AVDECC_EXAMPLES=TRUE -DBUILD_AVDECC_CONTROLLER=TRUE \
      -DBUILD_AVDECC_INTERFACE_PCAP=TRUE -DENABLE_AVDECC_FEATURE_JSON=TRUE \
      -DBUILD_AVDECC_TESTS=FALSE -DENABLE_CODE_SIGNING=FALSE \
 && cmake --build /src/build --target ShowNetworkCollector -j2


# Keep the build image as runtime too: LA_avdecc's shared-library layout is
# then exactly the one CMake produced, avoiding fragile hand-copied .so paths.
FROM build AS runtime
COPY bridge_server.py /usr/local/bin/show-network-avdecc-bridge
COPY run.sh /usr/local/bin/show-network-avdecc-run
RUN chmod +x /usr/local/bin/show-network-avdecc-bridge /usr/local/bin/show-network-avdecc-run \
 && ln -s /src/build/examples/src/ShowNetworkCollector /usr/local/bin/show-network-avdecc-collector
VOLUME ["/data"]
EXPOSE 8765
CMD ["/usr/local/bin/show-network-avdecc-run"]
