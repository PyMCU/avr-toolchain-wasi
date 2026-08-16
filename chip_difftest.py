"""Per-chip differential: every chip PyMCU supports, every library subdirectory.

attiny13 (avr25/tiny-stack) against attiny85 (plain avr25) is the case the family
name gets wrong, so it matters more than the ones that look obvious.
"""
from __future__ import annotations

import hashlib, json, shutil, subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pymcu_wasi_toolchain import WasiToolchain, sha256

HERE = Path(__file__).resolve().parent
NATIVE = HERE / "native" / "pymcu_avr_toolchain"
TABLE = json.loads((HERE / "cc1_flags.json").read_text())

# Uses only RJMP/RCALL and 16-bit maths, so it assembles on reduced-core parts
# too, and pulls __divmodhi4 out of libgcc -- the one division helper that
# exists in every variant -- so the library choice actually reaches the image.
SRC = """\
.global main
main:
\tLDI\tr24, 0x2A
\tLDI\tr25, 0x00
\tLDI\tr22, 0x03
\tLDI\tr23, 0x00
\tRCALL\t__divmodhi4
\tSTS\t0x0100, r24
\tRJMP\tmain
"""

LD = """\
OUTPUT_FORMAT("elf32-avr","elf32-avr","elf32-avr")
ENTRY(main)
SECTIONS
{
  .text 0x000000 : { *(.vectors) *(.text*) *(.rodata*) . = ALIGN(2); }
  .data 0x%06X : { *(.data*) *(.bss*) *(COMMON) . = ALIGN(1); }
}
"""

RAMSTART = {"attiny13": 0x60, "attiny13a": 0x60, "attiny24": 0x60, "attiny25": 0x60,
            "attiny44": 0x60, "attiny45": 0x60, "attiny84": 0x60, "attiny85": 0x60,
            "attiny2313": 0x60, "attiny4313": 0x60}


def build(chip: str, emu: str, libdir: str, work: Path, tc: WasiToolchain) -> tuple[str, str]:
    work.mkdir(parents=True, exist_ok=True)
    origin = 0x800000 + RAMSTART.get(chip, 0x100)
    (work / "firmware.asm").write_text(SRC)
    (work / "_pymcu.ld").write_text(LD % origin)
    gcc_lib = NATIVE / "lib" / "gcc" / "avr" / "14.2.0" / libdir
    avr_lib = NATIVE / "avr" / "lib" / libdir
    b = NATIVE / "bin"

    subprocess.run([str(b/"avr-as"), f"-mmcu={chip}", "-mno-skip-bug",
                    "firmware.asm", "-o", "n.o"], cwd=work, check=True, capture_output=True)
    subprocess.run([str(b/"avr-ld"), f"-m{emu}", "-Tdata", f"0x{origin:06X}", "--relax",
                    "-o", "n.elf", f"-L{gcc_lib}", f"-L{avr_lib}", "n.o", "-lm", "-lgcc",
                    "-T", "_pymcu.ld"], cwd=work, check=True, capture_output=True)
    subprocess.run([str(b/"avr-objcopy"), "-O", "ihex", "-R", ".eeprom", "n.elf", "n.hex"],
                   cwd=work, check=True, capture_output=True)

    lib = work / "lib"
    lib.mkdir(exist_ok=True)
    shutil.copy(gcc_lib / "libgcc.a", lib / "libgcc.a")
    shutil.copy(avr_lib / "libm.a", lib / "libm.a")
    tc.run("avr-as", [f"-mmcu={chip}", "-mno-skip-bug",
                      "/work/firmware.asm", "-o", "/work/w.o"], work)
    tc.run("avr-ld", [f"-m{emu}", "-Tdata", f"0x{origin:06X}", "--relax",
                      "-o", "/work/w.elf", "-L/work/lib", "/work/w.o", "-lm", "-lgcc",
                      "-T", "/work/_pymcu.ld"], work)
    tc.run("avr-objcopy", ["-O", "ihex", "-R", ".eeprom", "/work/w.elf", "/work/w.hex"], work)
    return sha256(work / "n.hex"), sha256(work / "w.hex")


def main() -> int:
    root = HERE / "t" / "chips"
    shutil.rmtree(root, ignore_errors=True)
    tc = WasiToolchain()
    ok = bad = 0
    seen = {}
    for chip, entry in TABLE.items():
        emu = next(f.split("=")[1] for f in entry["flags"] if f.startswith("-mmcu="))
        libdir = entry["libdir"]
        try:
            n, w = build(chip, emu, libdir, root / chip, tc)
        except Exception as exc:
            print(f"SKIP  {chip:<12} {str(exc)[:70]}")
            continue
        tag = "same" if n == w else "DIFF"
        ok, bad = (ok + 1, bad) if n == w else (ok, bad + 1)
        seen.setdefault(libdir or "(raiz)", []).append(chip)
        print(f"{tag}  {chip:<12} libdir={libdir or '(raiz)':<18} {n[:16]}")
    print()
    print("subdirectorios de biblioteca cubiertos:")
    for libdir, chips in sorted(seen.items()):
        print(f"  {libdir:<20} {len(chips)} chips")
    print(f"\nidenticos={ok}  distintos={bad}")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
