"""End-to-end FFI check through the driver.

Drives pymcu-avr's AvrgasToolchain -- compile_c / assemble / link / elf_to_hex --
with both WASI wheels installed and no native toolchain in the interpreter, and
compares each .hex against the native reference.

The reference hashes are the ones from the matched-version run
(ffi_matched_test.sh): a native avr-gcc 15.2.0 against the same 15.2.0 front ends
on wasmtime, which is where "identical" was actually established. Comparing
against the 14.2.0 wheel here would only re-measure the compiler version.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

from rich.console import Console

from pymcu.toolchain.avr.avrgas import AvrgasToolchain

HERE = Path(__file__).resolve().parent
NATIVE = HERE / "native" / "pymcu_avr_toolchain"
EXAMPLES = Path.home() / "Repos" / "pymcu-avr" / "examples"
GCC_VER = "14.2.0"

sys.path.insert(0, str(HERE))
import ffi_difftest as F  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# From ffi_matched_test.sh: native avr-gcc 15.2.0 vs cc1/cc1plus 15.2.0 on wasm.
EXPECTED = {
    "extern-call": "19a02b9543bb2c4b",
    "ffi-abi": "59b479fb17c66d89",
    "ffi-arduino": "48e4151fc0e677ce",
    "ffi-crc8": "aa782f74cce5506c",
    "ffi-dsp": "06d6b7856a2c83ed",
    "cpp-case": "8ac3908121ebe5a5",
}


def main() -> int:
    root = HERE / "t" / "driver-ffi"
    shutil.rmtree(root, ignore_errors=True)
    console = Console()

    targets = [p for p in sorted(EXAMPLES.iterdir())
               if (p / "pyproject.toml").exists()
               and "[tool.pymcu.ffi]" in (p / "pyproject.toml").read_text()
               and (p / "dist" / "debug" / "firmware.asm").exists()]
    targets.append(HERE / "t" / "cpp-case")

    AvrgasToolchain._preprocess_asm = staticmethod(lambda src, has_jmp=True: src)

    ok = bad = skipped = 0
    t_wasi = 0.0
    for example in targets:
        chip = F.chip_of(example)
        sources, incdirs, cflags = F.ffi_config(example)
        if not sources:
            skipped += 1
            continue
        emu = F.FLAGS[chip]
        emu = next(f.split("=")[1] for f in emu["flags"] if f.startswith("-mmcu="))
        multilib = F.FLAGS[chip]["libdir"]

        expected = EXPECTED.get(example.name)
        if expected is None:
            skipped += 1
            continue

        work = root / example.name / "wasi"
        work.mkdir(parents=True, exist_ok=True)
        shutil.copy(example / "dist" / "debug" / "firmware.asm", work / "firmware.asm")
        shutil.copy(example / "dist" / "_pymcu.ld", work / "_pymcu.ld")

        tc = AvrgasToolchain(console, chip=chip)
        pipeline = tc._wasi_pipeline()
        if pipeline is None or pipeline.ffi is None:
            print("el extra [ffi] de WASI no esta disponible")
            return 2
        try:
            t0 = time.perf_counter()
            objects = tc.compile_c(sources, incdirs, cflags, work)
            obj = tc.assemble(work / "firmware.asm")
            elf = tc.link(obj, objects, work, work / "_pymcu.ld")
            hex_file = tc.elf_to_hex(elf)
            t_wasi += time.perf_counter() - t0
        except Exception as exc:  # noqa: BLE001
            bad += 1
            print(f"FAIL  {example.name}: {exc}")
            continue

        got = sha256(hex_file)[:16]
        if got == expected:
            ok += 1
            print(f"same  {example.name:<14} {got}")
        else:
            bad += 1
            print(f"DIFF  {example.name:<14} esperado={expected} obtenido={got}")

    print()
    print(f"driver + WASI FFI: identicos={ok} distintos/fallidos={bad} saltados={skipped}")
    print(f"tiempo wasi: {t_wasi:.2f}s")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
