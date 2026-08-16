#!/bin/bash
# Native avr-gcc 15.2.0, so the wasm cc1 can be compared against a cc1 of the
# very same version instead of against the 14.2.0 wheel.
set -e -o pipefail
GCC_SRC=/src/gcc-15.2.0
mkdir -p /build/native-gcc && cd /build/native-gcc
if [ ! -f Makefile ]; then
  "$GCC_SRC/configure" --target=avr --prefix=/opt/avr-native \
    --enable-languages=c,c++ --disable-nls --disable-libssp --disable-libada \
    --disable-shared --disable-threads --disable-libgomp --disable-libquadmath \
    --disable-libatomic --disable-libstdcxx --without-headers --disable-lto \
    --with-as=/opt/avr-native/bin/avr-as --with-ld=/opt/avr-native/bin/avr-ld >/dev/null
fi
make -j"$(nproc)" MAKEINFO=true all-gcc
make install-gcc MAKEINFO=true >/dev/null
ls -l /opt/avr-native/libexec/gcc/avr/15.2.0/cc1 /opt/avr-native/libexec/gcc/avr/15.2.0/cc1plus
