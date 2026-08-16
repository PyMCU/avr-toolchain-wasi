"""End-to-end check of the driver integration.

Drives pymcu-avr's AvrgasToolchain -- assemble / link / elf_to_hex -- with the
WASI backend active, and compares each .hex against the sha256 the native
toolchain produces. Nothing native is installed in this interpreter.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

from rich.console import Console

from pymcu.toolchain.avr.avrgas import AvrgasToolchain

HERE = Path(__file__).resolve().parent
BUNDLE = HERE / "verify-bundle"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    cases = json.loads((BUNDLE / "manifest.json").read_text())
    work_root = HERE / "t" / "driver"
    shutil.rmtree(work_root, ignore_errors=True)
    console = Console()

    # The bundled firmware.asm files are the driver's own output, i.e. already
    # translated to GNU AS syntax -- and _preprocess_asm is not idempotent
    # (a second pass eats half the vector table). The driver runs it exactly
    # once on the raw pymcuc output, so for this comparison it is a no-op.
    AvrgasToolchain._preprocess_asm = staticmethod(lambda src, has_jmp=True: src)

    ok = bad = 0
    for case in cases:
        chip = case["chip"]
        src = BUNDLE / "cases" / case["name"]
        out = work_root / case["name"]
        out.mkdir(parents=True)
        shutil.copy(src / "firmware.asm", out / "firmware.asm")

        tc = AvrgasToolchain(console, chip=chip)
        if tc._wasi_pipeline() is None:
            print("WASI backend no disponible")
            return 2
        try:
            obj = tc.assemble(out / "firmware.asm")
            elf = tc.link(obj, [], out)
            hex_file = tc.elf_to_hex(elf)
        except Exception as exc:
            bad += 1
            print(f"FAIL  {case['name']}: {exc}")
            continue

        if sha256(hex_file) == case["sha256"]:
            ok += 1
        else:
            bad += 1
            print(f"DIFF  {case['name']}: esperado {case['sha256'][:16]} "
                  f"obtenido {sha256(hex_file)[:16]}")

    print(f"driver + WASI: identicos={ok} distintos/fallidos={bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
