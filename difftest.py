"""Differential harness: native binutils vs wasm32-wasip1 binutils.

For every prebuilt PyMCU AVR example it runs the same as/ld/objcopy pipeline
through both toolchains and compares the .hex by sha256.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import time
from pathlib import Path

from pymcu_wasi_toolchain import WasiToolchain, build_hex, sha256

HERE = Path(__file__).resolve().parent
NATIVE = HERE / "native" / "pymcu_avr_toolchain"
EXAMPLES = Path.home() / "Repos" / "pymcu-avr" / "examples"
GCC_VER = "14.2.0"

ARCH = {
    "atmega328p": "avr5",
    "atmega2560": "avr6",
    "atmega32u4": "avr5",
    "attiny85": "avr25",
    "attiny84": "avr25",
}


def native_build(asm: Path, ld_script: Path, work: Path, chip: str, emu: str) -> Path:
    work.mkdir(parents=True, exist_ok=True)
    shutil.copy(asm, work / "firmware.asm")
    shutil.copy(ld_script, work / "_pymcu.ld")
    bin_ = NATIVE / "bin"
    libgcc = NATIVE / "lib" / "gcc" / "avr" / GCC_VER / emu
    libavr = NATIVE / "avr" / "lib" / emu
    subprocess.run([str(bin_ / "avr-as"), f"-mmcu={chip}", "-mno-skip-bug",
                    "firmware.asm", "-o", "firmware.o"],
                   cwd=work, check=True, capture_output=True)
    subprocess.run([str(bin_ / "avr-ld"), f"-m{emu}", "-Tdata", "0x800100", "--relax",
                    "-o", "firmware.elf", f"-L{libgcc}", f"-L{libavr}",
                    "firmware.o", "-lm", "-lgcc", "-T", "_pymcu.ld"],
                   cwd=work, check=True, capture_output=True)
    subprocess.run([str(bin_ / "avr-objcopy"), "-O", "ihex", "-R", ".eeprom",
                    "firmware.elf", "firmware.hex"],
                   cwd=work, check=True, capture_output=True)
    return work / "firmware.hex"


def chip_of(example: Path) -> str:
    pyproject = example / "pyproject.toml"
    if pyproject.exists():
        for line in pyproject.read_text().splitlines():
            if line.strip().startswith("target"):
                return line.split("=", 1)[1].strip().strip('"')
    return "atmega328p"


def main() -> int:
    out_root = HERE / "t" / "diff"
    shutil.rmtree(out_root, ignore_errors=True)
    tc = WasiToolchain()

    ok = diff = skipped = 0
    wasi_total = native_total = 0.0
    rows: list[tuple[str, str]] = []

    for example in sorted(EXAMPLES.iterdir()):
        asm = example / "dist" / "debug" / "firmware.asm"
        ld_script = example / "dist" / "_pymcu.ld"
        if not (asm.exists() and ld_script.exists()):
            continue
        chip = chip_of(example)
        emu = ARCH.get(chip, "avr5")
        libgcc = NATIVE / "lib" / "gcc" / "avr" / GCC_VER / emu / "libgcc.a"
        libm = NATIVE / "avr" / "lib" / emu / "libm.a"

        n_work = out_root / example.name / "native"
        w_work = out_root / example.name / "wasi"
        try:
            t0 = time.perf_counter()
            n_hex = native_build(asm, ld_script, n_work, chip, emu)
            native_total += time.perf_counter() - t0
        except subprocess.CalledProcessError as exc:
            rows.append((example.name, "SKIP native: " + exc.stderr.decode()[:90].strip()))
            skipped += 1
            continue
        try:
            t0 = time.perf_counter()
            w_hex, _ = build_hex(tc, asm, ld_script, libgcc, libm, w_work, chip, emu)
            wasi_total += time.perf_counter() - t0
        except RuntimeError as exc:
            rows.append((example.name, "FAIL wasi: " + str(exc)[:90].strip()))
            diff += 1
            continue

        if sha256(n_hex) == sha256(w_hex):
            ok += 1
            rows.append((example.name, "same " + sha256(n_hex)[:16]))
        else:
            diff += 1
            rows.append((example.name, f"DIFF native={sha256(n_hex)[:16]} wasi={sha256(w_hex)[:16]}"))

    width = max(len(r[0]) for r in rows) if rows else 10
    for name, status in rows:
        print(f"{name:<{width}}  {status}")
    print()
    print(f"identical: {ok}   different/failed: {diff}   skipped: {skipped}")
    print(f"wall time  wasi: {wasi_total:.2f}s   native: {native_total:.2f}s")
    return 0 if diff == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
