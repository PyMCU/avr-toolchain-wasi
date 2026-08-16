#!/bin/bash
# Builds avr-as / avr-ld / avr-objcopy as wasm32-wasip1 modules with wasi-sdk.
set -e -o pipefail

ROOT=$(cd "$(dirname "$0")" && pwd)
SDK="${WASI_SDK:-$ROOT/wasi-sdk}"
SRC="${SRC:-$ROOT/binutils-2.42}"
BUILD="${BUILD:-$ROOT/build}"
DIST="${DIST:-$ROOT/dist}"
SHIM="${SHIM:-$ROOT/wasi-shim.h}"

SYSROOT="$SDK/share/wasi-sysroot"
BUILD_TRIPLET=$("$SRC/config.guess")
NPROC=$(command -v nproc >/dev/null && nproc || sysctl -n hw.ncpu)

export CC="$SDK/bin/clang"
export CXX="$SDK/bin/clang++"
export AR="$SDK/bin/llvm-ar"
export RANLIB="$SDK/bin/llvm-ranlib"
export NM="$SDK/bin/llvm-nm"
export STRIP="$SDK/bin/llvm-strip"
export CC_FOR_BUILD=cc
export CXX_FOR_BUILD=c++

EMU="-D_WASI_EMULATED_SIGNAL -D_WASI_EMULATED_PROCESS_CLOCKS -D_WASI_EMULATED_MMAN -D_WASI_EMULATED_GETPID"
export CFLAGS="--sysroot=$SYSROOT -Os -DHAVE_PSIGNAL=1 -DELIDE_CODE -DHAVE_STRSIGNAL=1 -include $SHIM -Wno-unused-parameter $EMU"
export CXXFLAGS="$CFLAGS"
export LDFLAGS="--sysroot=$SYSROOT -lwasi-emulated-signal -lwasi-emulated-process-clocks -lwasi-emulated-mman -lwasi-emulated-getpid -Wl,-z,stack-size=8388608"

perl -pi -e 's/^development=true/development=false/' "$SRC/bfd/development.sh"

CONFIG_SITE="$ROOT/config.site"
cat > "$CONFIG_SITE" <<'EOF'
am_cv_ar_has_plugin=no
EOF
export CONFIG_SITE

mkdir -p "$BUILD" "$DIST"
cd "$BUILD"

if [ ! -f Makefile ]; then
  "$SRC/configure" \
    --build="$BUILD_TRIPLET" \
    --host=wasm32-wasi \
    --target=avr \
    --prefix=/opt/avr \
    --enable-deterministic-archives \
    --enable-default-execstack=no \
    --enable-ld=default \
    --disable-doc \
    --disable-gprof \
    --disable-nls \
    --disable-gdb \
    --disable-gdbserver \
    --disable-libdecnumber \
    --disable-readline \
    --disable-sim \
    --disable-werror \
    --disable-plugins \
    --disable-libctf \
    --disable-gprofng \
    --without-zstd \
    --without-msgpack \
    --without-debuginfod
fi

make -j"$NPROC" MAKEINFO=true all-gas all-ld all-binutils

install -m 0755 gas/as-new "$DIST/avr-as.wasm"
install -m 0755 ld/ld-new "$DIST/avr-ld.wasm"
install -m 0755 binutils/objcopy "$DIST/avr-objcopy.wasm"
"$SDK/bin/llvm-strip" "$DIST"/avr-as.wasm "$DIST"/avr-ld.wasm "$DIST"/avr-objcopy.wasm
ls -l "$DIST"
