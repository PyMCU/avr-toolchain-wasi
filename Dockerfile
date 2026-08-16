FROM debian:bookworm AS builder

ARG WASI_SDK_VERSION=33
ARG WASI_SDK_FULL=33.0
ARG BINUTILS=2.42

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential curl ca-certificates xz-utils perl bison flex && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN arch=$(uname -m) && [ "$arch" = aarch64 ] && arch=arm64 || true; \
    curl -fsSL -o /tmp/wasi-sdk.tar.gz \
      "https://github.com/WebAssembly/wasi-sdk/releases/download/wasi-sdk-${WASI_SDK_VERSION}/wasi-sdk-${WASI_SDK_FULL}-${arch}-linux.tar.gz" && \
    mkdir -p /opt/wasi-sdk && \
    tar xzf /tmp/wasi-sdk.tar.gz -C /opt/wasi-sdk --strip-components=1 && \
    rm /tmp/wasi-sdk.tar.gz

RUN curl -fsSL -o /tmp/binutils.tar.xz \
      "https://ftp.gnu.org/gnu/binutils/binutils-${BINUTILS}.tar.xz" && \
    mkdir -p /src_root && \
    tar xf /tmp/binutils.tar.xz -C /src_root && \
    rm /tmp/binutils.tar.xz

WORKDIR /work
COPY build.sh wasi-shim.h /work/
ENV WASI_SDK=/opt/wasi-sdk
RUN SRC=/src_root/binutils-${BINUTILS} DIST=/dist BUILD=/build ./build.sh

FROM scratch AS export
COPY --from=builder /dist/ /
