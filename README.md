# avr-wasi

PyMCU's AVR toolchain as `wasm32-wasip1` modules: `avr-as`, `avr-ld` and
`avr-objcopy` built from binutils 2.42 with wasi-sdk 33, run from Python through
wasmtime. One architecture-independent wheel replaces five native builds.

Verified: the `.hex` is byte-identical (sha256) to the native toolchain's for the
53 non-FFI PyMCU AVR examples, from five hosts running the same three modules —
Linux x86_64, Linux aarch64, macOS arm64, Windows AMD64 and Windows ARM64 — plus
all 20 supported chips across the 5 library subdirectories, and the 6 FFI cases
(including C++) against a native avr-gcc of the same version. macOS Intel is
unverified: GitHub retired the `macos-13` runner.

`cc1` and `cc1plus` build for wasi too, so the FFI path needs no native compiler
either; they ship in a separate wheel because they are large.

## Layout

| Path | What |
|---|---|
| `build.sh` | binutils -> wasm recipe (host build, needs `./wasi-sdk`) |
| `Dockerfile` | the same recipe, reproducible on Linux/CI |
| `wasi-shim.h` | the ten libc functions wasi-libc lacks (`mktemp`, `umask`, process stubs) |
| `pymcu_wasi_toolchain.py` | standalone orchestrator: as -> ld -> objcopy |
| `difftest.py` | differential harness, native vs WASI, over the examples |
| `driver_difftest.py` | same, but driving pymcu-avr's `AvrgasToolchain` |
| `verify.py`, `make_verify_bundle.py` | self-contained bundle for other platforms |
| `windows-verify.yml` | GitHub Actions matrix including Windows x64 and arm64 |
| `repro_preprocess_asm.py` | minimal reproducer for the non-idempotent `_preprocess_asm` (driver bug, unrelated to WASI) |
| `wheel/` | `pymcu-avr-toolchain-wasi`, `py3-none-any`, 1.7 MB |
| `wheel-ffi/` | `pymcu-avr-toolchain-wasi-ffi` (cc1 + cc1plus + headers), 21 MB |
| `gen_cc1_table.py` | regenerates `cc1_flags.json` by asking avr-gcc, for PyMCU's own chip list |
| `chip_difftest.py` | per-chip differential over all 20 chips and 5 library subdirectories |
| `ffi_matched_test.sh` | native avr-gcc 15.2.0 vs the same version on wasm, in-container |
| `driver_ffi_difftest.py` | the FFI path end to end through pymcu-avr's toolchain |
| `sysroot-min/` | `libgcc.a` + `libm.a` per emulation, `--strip-debug` |
| `Dockerfile.cc1`, `build-cc1.sh`, `wasi-shim-gcc.h` | gcc's `cc1` and `cc1plus` for wasi (the FFI extra) |

## Build

```bash
docker build --output type=local,dest=./dist-docker -f Dockerfile .
```

Or on the host, with wasi-sdk unpacked and symlinked as `./wasi-sdk`:

```bash
./build.sh
```

## Check

```bash
python -m venv .venv && .venv/bin/pip install wasmtime
.venv/bin/python difftest.py
```

The bundle in `verify-bundle/` needs only `pip install wasmtime`; it carries the
cases and the reference hashes, so it runs anywhere:

```bash
cd verify-bundle && python verify.py
```
