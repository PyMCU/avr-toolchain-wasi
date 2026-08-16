# avr-toolchain-wasi

The AVR toolchain as WebAssembly. `avr-as`, `avr-ld`, `avr-objcopy`, `cc1` and
`cc1plus` built for `wasm32-wasip1` and driven from Python through
[wasmtime](https://wasmtime.dev/) — **one architecture-independent wheel instead
of a native build per platform**.

```bash
pip install pymcu-avr-toolchain-wasi
```

Built for [PyMCU](https://github.com/PyMCU/PyMCU), which compiles Python to
native microcontroller code.

## Why

Shipping a native toolchain means building and maintaining it for every platform
a user might have. In practice that is where the time goes, and none of it is
the compiler's fault: Rosetta 2 missing on a new Mac, MSYS2's `config.guess`
making a native build look like a cross, `uname -m` saying `x86_64` while
`file` says `x86-64`, GCC 14 sources refusing to compile against a 2026
libstdc++. Six consecutive failed attempts on Windows alone.

The same modules run everywhere wasmtime does. That class of problem disappears.

|  | native, per platform | this |
|---|---|---|
| Artifacts to build | 5 | **0** |
| Wheel | 70.7 MB | **22.9 MB** |
| Installed | 226 MB | **105 MB** |
| Platforms | 5, each verified separately | anywhere wasmtime runs |

It is also *faster* in real use — 0.27 s against 0.51 s for 53 builds — because
the module is compiled once and each build is a fresh instance, with no
`fork`/`exec` per tool.

## Verified, not assumed

Every firmware is compared to the native toolchain's output **by sha256**, not by
whether the build succeeded:

```
Linux x86_64    plain 53/53   FFI 6/6   TOTAL 59/59
Linux aarch64   plain 53/53   FFI 6/6   TOTAL 59/59
macOS arm64     plain 53/53   FFI 6/6   TOTAL 59/59
Windows AMD64   plain 53/53   FFI 6/6   TOTAL 59/59
Windows ARM64   plain 53/53   FFI 6/6   TOTAL 59/59
```

The same five modules on all five runners. The FFI cases cover `@extern` with C
sources and one C++ case (class, method, template, `extern "C"`). Also verified
across 20 chips and the five library subdirectories, and against binutils 2.45.1
and a libgcc from GCC 9.5.0 — neither changes a byte of firmware.

**macOS Intel is not verified.** GitHub retired the `macos-13` runner, so there
is nowhere to measure it. `wasmtime` publishes a `macosx_10_13_x86_64` wheel, so
there is reason to expect it works, but that is an expectation and not a
measurement.

## How it works

WASI has no `fork`/`exec`, so the GCC driver cannot be ported — it is replaced.
The exact command line each tool needs is taken from `avr-gcc -###` rather than
reconstructed by hand, and tabulated per chip:

```
avr-as   -mmcu=<chip> -mno-skip-bug firmware.asm -o firmware.o
avr-ld   -m <emulation> -Tdata 0x<800000+RAMSTART> --relax firmware.o
         -L<libgcc/libdir> -L<avr/lib/libdir> --start-group -lgcc -lm --end-group
objcopy  -O ihex -R .eeprom firmware.elf firmware.hex
```

Deriving those tables from the compiler instead of from the chip's name is not
pedantry. It caught three defects that would have produced broken firmware
silently:

- `atmega1280` is `avr51`, not `avr6` as the family name suggests.
- `attiny13`, `13a`, `24`, `25` and `2313` are `avr25` for the linker but must
  link against **`avr25/tiny-stack`**, the 8-bit stack pointer variant. The wrong
  one emits code that writes `SPH` on parts that have no `SPH`.
- A hand-maintained chip list had drifted from the one the product supports. The
  table is now generated from PyMCU's own chip directory, so it cannot.

## Building

The modules are built in a container and the recipe is reproducible:

```bash
docker build --output type=local,dest=./dist-docker -f Dockerfile .      # as/ld/objcopy
docker build --output type=local,dest=./dist-ffi   -f Dockerfile.cc1 .   # cc1/cc1plus
```

What is reproducible is the **firmware**: modules built on macOS and in the
container differ in size yet produce identical `.hex`. Bit-identical modules
across build hosts is a separate problem and is not claimed here.

Build products, SDKs and caches are deliberately absent from this repository —
CI assembles the wheel from the verified payload attached to each release, so
what reaches PyPI is what was measured, not a rebuild nobody checked.

## Harnesses

```bash
python difftest.py            # 53 plain examples, native vs wasi
python ffi_difftest.py        # the FFI path
python chip_difftest.py       # 20 chips across 5 library subdirectories
python driver_difftest.py     # through PyMCU's own driver
```

## Limits

- **Programmers stay native.** `avrdude` talks to a serial port; WASI does not.
- **C++ with global constructors does not link**, and does not link natively
  either: it emits `__do_global_ctors` and `__do_clear_bss`, which PyMCU's
  `-nostartfiles` link and its own linker script do not provide. That is a
  linker-script matter, not a toolchain one.
- Roughly 2× slower than native on inputs of megabytes — far above anything that
  fits in an AVR.

## Licence

GPL-3.0-or-later, as the GNU toolchain it is built from.
