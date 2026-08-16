#!/bin/bash
# Runs the FFI differential inside the container, comparing a native avr-gcc
# 15.2.0 against the cc1/cc1plus of the very same version running on wasmtime.
set -e
NAT=/opt/avr-native
CC1_NATIVE=$NAT/libexec/gcc/avr/15.2.0/cc1
CC1PLUS_NATIVE=$NAT/libexec/gcc/avr/15.2.0/cc1plus
W=/host
OUT=/tmp/ffi
rm -rf $OUT; mkdir -p $OUT

same=0; diff=0
for case_dir in "$@"; do
  name=$(basename "$case_dir")
  d=$OUT/$name; mkdir -p $d/n $d/w
  # Sources and flags are passed by the caller through env files.
  src=$(cat "$case_dir/.src")
  inc=$(cat "$case_dir/.inc")
  extra=$(cat "$case_dir/.extra")
  chip=$(cat "$case_dir/.chip")
  emu=$(cat "$case_dir/.emu")
  lib=$(cat "$case_dir/.lib")
  flags=$(cat "$case_dir/.flags")
  cp "$case_dir"/firmware.asm "$case_dir"/_pymcu.ld $d/n/
  cp "$case_dir"/firmware.asm "$case_dir"/_pymcu.ld $d/w/
  cp "$case_dir"/srcs/* $d/n/ 2>/dev/null || true
  cp "$case_dir"/srcs/* $d/w/ 2>/dev/null || true

  base=$(basename "$src")
  stem="${base%.*}"
  case "$base" in
    *.cpp|*.cc|*.cxx) NATIVE_CC1=$CC1PLUS_NATIVE; WASM=/host/cc1plus.wasm ;;
    *) NATIVE_CC1=$CC1_NATIVE; WASM=/host/cc1.wasm ;;
  esac

  ( cd $d/n && $NATIVE_CC1 -quiet -nostdinc \
      -isystem /host/sysroot-ffi/gcc -isystem /host/sysroot-ffi/gcc-fixed \
      -isystem /host/sysroot-ffi/avr -I . \
      $flags -mno-skip-bug -Os $extra "$base" -o "$stem.s" )
  ( cd $d/w && wasmtime run --dir=.::/work --dir=/host/sysroot-ffi::/inc $WASM \
      -quiet -nostdinc -isystem /inc/gcc -isystem /inc/gcc-fixed -isystem /inc/avr \
      -I /work $flags -mno-skip-bug -Os $extra "/work/$base" -o "/work/$stem.s" )

  for v in n w; do
    ( cd $d/$v && $NAT/bin/avr-as -mmcu=$chip -mno-skip-bug "$stem.s" -o "$stem.o" \
      && $NAT/bin/avr-as -mmcu=$chip -mno-skip-bug firmware.asm -o firmware.o \
      && $NAT/bin/avr-ld -m$emu -Tdata 0x800100 --relax -o firmware.elf \
           -L$NAT/lib/gcc/avr/15.2.0/$lib -L/host/native/pymcu_avr_toolchain/avr/lib/$lib \
           firmware.o "$stem.o" -lm -lgcc -T _pymcu.ld \
      && $NAT/bin/avr-objcopy -O ihex -R .eeprom firmware.elf firmware.hex )
  done

  hn=$(sha256sum $d/n/firmware.hex | cut -d' ' -f1)
  hw=$(sha256sum $d/w/firmware.hex | cut -d' ' -f1)
  if [ "$hn" = "$hw" ]; then same=$((same+1)); echo "same  $name  ${hn:0:16}";
  else diff=$((diff+1)); echo "DIFF  $name  nativo=${hn:0:16} wasi=${hw:0:16}"; fi
done
echo
echo "identicos=$same  distintos=$diff"
[ $diff -eq 0 ]
