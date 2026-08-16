#!/bin/bash
# Scoping probe: can gcc's cc1 (the C front end) be built for wasm32-wasip1?
# build = linux, host = wasm32-wasi, target = avr -- a canadian cross.
set -e -o pipefail

SDK="${WASI_SDK:-/opt/wasi-sdk}"
GCC_SRC="${GCC_SRC:?set GCC_SRC}"
SYSROOT="$SDK/share/wasi-sysroot"
SHIM="${SHIM:-/work/wasi-shim-gcc.h}"

export PATH="/opt/avr-native/bin:$PATH"

export CC_FOR_BUILD=cc
export CXX_FOR_BUILD=c++
export BUILD_CC=cc
# The build-machine programs (build-libcpp, genfoo, ...) must NOT inherit the
# wasi sysroot; without this they fail with "no include path for stdint.h".
export CFLAGS_FOR_BUILD="-O2"
export CXXFLAGS_FOR_BUILD="-O2"
export LDFLAGS_FOR_BUILD=""
export BUILD_CPPFLAGS=""
export CC="$SDK/bin/clang"
export CXX="$SDK/bin/clang++"
export AR="$SDK/bin/llvm-ar"
export RANLIB="$SDK/bin/llvm-ranlib"
export NM="$SDK/bin/llvm-nm"

EMU="-D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_MMAN -D_WASI_EMULATED_GETPID"
HOST_CFLAGS="--sysroot=$SYSROOT -O1 -include $SHIM -Wno-unused-parameter $EMU"
HOST_LDFLAGS="--sysroot=$SYSROOT -lwasi-emulated-signal -lwasi-emulated-process-clocks -lwasi-emulated-mman -lwasi-emulated-getpid -Wl,-z,stack-size=16777216"

# CFLAGS/CXXFLAGS are passed as configure arguments, never exported: gcc's
# build-machine subdirectories (build-libcpp, fixincludes, gen*) inherit the
# environment and would then be compiled against the wasi sysroot.
unset CFLAGS CXXFLAGS LDFLAGS

rm -rf "$GCC_SRC/gettext"

# The in-tree gmp/mpfr/mpc/isl copies pulled by download_prerequisites carry
# their own config.sub, too old to know wasm32-wasi. Refresh them from gcc's.
for dep in gmp mpfr mpc isl; do
  for f in config.sub config.guess; do
    [ -f "$GCC_SRC/$dep/$f" ] && cp "$GCC_SRC/$f" "$GCC_SRC/$dep/$f"
    [ -f "$GCC_SRC/$dep/./$f" ] && cp "$GCC_SRC/$f" "$GCC_SRC/$dep/$f"
  done
done

mkdir -p /build/gcc && cd /build/gcc

"$GCC_SRC/configure" \
  --build="$($GCC_SRC/config.guess)" \
  --host=wasm32-wasi \
  --target=avr \
  --prefix=/opt/avr \
  --enable-languages=c,c++ \
  --disable-nls \
  --disable-shared \
  --disable-threads \
  --disable-libssp \
  --disable-libgomp \
  --disable-libquadmath \
  --disable-libatomic \
  --disable-libstdcxx \
  --disable-lto \
  --disable-plugin \
  --disable-fixincludes \
  --without-isl \
  --without-headers \
  --with-as=/opt/avr-native/bin/avr-as \
  --with-ld=/opt/avr-native/bin/avr-ld \
  CFLAGS="$HOST_CFLAGS" \
  CXXFLAGS="$HOST_CFLAGS" \
  LDFLAGS="$HOST_LDFLAGS" \
  CFLAGS_FOR_BUILD="-O2" \
  CXXFLAGS_FOR_BUILD="-O2" \
  LDFLAGS_FOR_BUILD=""

# EXTRA_BUILD_FLAGS is what gcc's toplevel hands to the build-machine modules,
# and upstream it only carries CFLAGS/LDFLAGS -- CXXFLAGS leaks in from the host
# configuration, which is why build-libcpp (C++) picks up the wasi sysroot.
make -j"$(nproc)" MAKEINFO=true \
  CFLAGS_FOR_BUILD="-O2" CXXFLAGS_FOR_BUILD="-O2" LDFLAGS_FOR_BUILD="" \
  EXTRA_BUILD_FLAGS='CFLAGS=-O2 CXXFLAGS=-O2 LDFLAGS=' \
  all-gcc
ls -l gcc/cc1 gcc/cc1plus
