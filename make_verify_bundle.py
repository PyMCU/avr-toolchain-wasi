"""Builds a self-contained verification bundle that reproduces the AVR
toolchain differential on any platform with Python 3.9+ and `pip install wasmtime`.

The bundle carries the three .wasm modules, the minimal AVR sysroot, every
example's firmware.asm / _pymcu.ld, and the sha256 each .hex must have -- the
values produced by the native binutils 2.42 toolchain on macOS arm64.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import difftest as D
from pymcu_wasi_toolchain import sha256

HERE = Path(__file__).resolve().parent
OUT = HERE / "verify-bundle"


def main() -> None:
    shutil.rmtree(OUT, ignore_errors=True)
    (OUT / "cases").mkdir(parents=True)
    shutil.copytree(HERE / "dist-docker", OUT / "wasm")
    shutil.copytree(HERE / "sysroot-min", OUT / "sysroot")
    shutil.copy(HERE / "pymcu_wasi_toolchain.py", OUT / "pymcu_wasi_toolchain.py")
    shutil.copy(HERE / "verify.py", OUT / "verify.py")

    manifest = []
    for example in sorted(D.EXAMPLES.iterdir()):
        asm = example / "dist" / "debug" / "firmware.asm"
        ld = example / "dist" / "_pymcu.ld"
        ref = HERE / "t" / "diff" / example.name / "native" / "firmware.hex"
        if not (asm.exists() and ld.exists() and ref.exists()):
            continue
        case = OUT / "cases" / example.name
        case.mkdir()
        shutil.copy(asm, case / "firmware.asm")
        shutil.copy(ld, case / "_pymcu.ld")
        chip = D.chip_of(example)
        manifest.append({
            "name": example.name,
            "chip": chip,
            "emulation": D.ARCH.get(chip, "avr5"),
            "sha256": sha256(ref),
        })

    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"{len(manifest)} casos -> {OUT}")


if __name__ == "__main__":
    main()
