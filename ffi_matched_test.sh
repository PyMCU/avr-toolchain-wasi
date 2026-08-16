#!/bin/bash
# Native avr-gcc 15.2.0 cc1/cc1plus vs the SAME version running on wasmtime.
# Both sides assemble and link identically with the wheel's binutils and libgcc,
# so the only variable left is where the front end ran.
set -u
NAT=/opt/avr-native
WHEEL=/host/native/pymcu_avr_toolchain
INC="-isystem /host/sysroot-ffi/gcc -isystem /host/sysroot-ffi/gcc-fixed -isystem /host/sysroot-ffi/avr"
OUT=/tmp/ffi; rm -rf $OUT; mkdir -p $OUT
same=0; diff=0; fail=0

for d in /host/t/ffi-cases/*/; do
  name=$(basename "$d")
  srcs=$(cat "$d/.srcs");  chip=$(cat "$d/.chip")
  emu=$(cat "$d/.emu");    lib=$(cat "$d/.lib")
  flags=$(cat "$d/.flags"); extra=$(cat "$d/.extra")

  for v in n w; do
    w=$OUT/$name/$v; mkdir -p "$w"
    cp "$d"/firmware.asm "$d"/_pymcu.ld "$w"/
    cp "$d"/srcs/* "$w"/ 2>/dev/null
  done

  objs=""
  for src in $srcs; do
    stem="${src%.*}"
    case "$src" in
      *.cpp|*.cc|*.cxx) FE=$NAT/libexec/gcc/avr/15.2.0/cc1plus; WASM=/host/cc1plus.wasm ;;
      *)                FE=$NAT/libexec/gcc/avr/15.2.0/cc1;     WASM=/host/cc1.wasm ;;
    esac
    ( cd $OUT/$name/n && $FE -quiet -nostdinc $INC -I . $flags -mno-skip-bug -Os $extra \
        "$src" -o "$stem.s" ) 2>> $OUT/$name/n.err
    ( cd $OUT/$name/w && wasmtime run --dir=.::/work --dir=/host/sysroot-ffi::/inc "$WASM" \
        -quiet -nostdinc -isystem /inc/gcc -isystem /inc/gcc-fixed -isystem /inc/avr \
        -I /work $flags -mno-skip-bug -Os $extra "/work/$src" -o "/work/$stem.s" ) 2>> $OUT/$name/w.err
    objs="$objs $stem.o"
  done

  for v in n w; do
    ( cd $OUT/$name/$v \
      && for src in $srcs; do st="${src%.*}"; $NAT/bin/avr-as -mmcu=$chip -mno-skip-bug "$st.s" -o "$st.o" || exit 1; done \
      && $NAT/bin/avr-as -mmcu=$chip -mno-skip-bug firmware.asm -o firmware.o \
      && $NAT/bin/avr-ld -m$emu -Tdata 0x800100 --relax -o firmware.elf \
           -L$WHEEL/lib/gcc/avr/14.2.0/$lib -L$WHEEL/avr/lib/$lib \
           firmware.o $objs -lm -lgcc -T _pymcu.ld \
      && $NAT/bin/avr-objcopy -O ihex -R .eeprom firmware.elf firmware.hex ) 2>> $OUT/$name/$v.err
  done

  if [ ! -s "$OUT/$name/n/firmware.hex" ] || [ ! -s "$OUT/$name/w/firmware.hex" ]; then
    fail=$((fail+1)); echo "FAIL(link) $name  $(tail -c 120 $OUT/$name/n.err)"
    continue
  fi
  hn=$(sha256sum $OUT/$name/n/firmware.hex | cut -d' ' -f1)
  hw=$(sha256sum $OUT/$name/w/firmware.hex | cut -d' ' -f1)
  sn=$(cat $OUT/$name/n/*.s | sha256sum | cut -d' ' -f1)
  sw=$(cat $OUT/$name/w/*.s | sha256sum | cut -d' ' -f1)
  asm_tag="asm=igual"; [ "$sn" = "$sw" ] || asm_tag="asm=DISTINTO"
  if [ "$hn" = "$hw" ]; then same=$((same+1)); echo "same  $name  hex=${hn:0:16}  $asm_tag"
  else diff=$((diff+1)); echo "DIFF  $name  nativo=${hn:0:16} wasi=${hw:0:16}  $asm_tag"; fi
done
echo
echo "identicos=$same  distintos=$diff  fallidos=$fail"
