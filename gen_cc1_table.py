"""Derives the per-chip cc1/cc1plus flags by asking avr-gcc, never by guessing.

`avr-gcc -mmcu=<chip> -### -c x.c` prints the exact cc1 argv the driver would
use. Everything chip-dependent lives there: the multilib directory, the device
macros and -mn-flash. None of it follows from the family name -- atmega1280 is
avr51 and attiny13 wants the avr25/tiny-stack multilib.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TC = Path(__file__).resolve().parent / "native" / "pymcu_avr_toolchain"
GCC = TC / "bin" / "avr-gcc"

# The chip list is PyMCU's own -- lib/src/pymcu/chips/ -- not a hand-written one.
# Anything outside it cannot be a build target, and anything inside it must
# resolve to a multilib the toolchain still ships (the wheel build prunes to
# KEEP_MULTILIBS="avr25 avr4 avr5 avr6"; avr25/tiny-stack survives inside avr25).
CHIPS_DIR = Path.home() / "Repos" / "PyMCU" / "lib" / "src" / "pymcu" / "chips"
CHIPS = sorted(
    f.stem for f in CHIPS_DIR.glob("*.py")
    if f.stem.startswith(("atmega", "attiny"))
)

KEEP = re.compile(r"^-(D__AVR_|mn-flash=|mdouble=|mlong-double=|mmcu=)")


def cc1_argv(chip: str, src: Path) -> list[str]:
    out = subprocess.run(
        [str(GCC), f"-mmcu={chip}", "-Os", "-c", str(src), "-o", "/dev/null", "-###"],
        capture_output=True, text=True,
    ).stderr
    for line in out.splitlines():
        if "/cc1" in line:
            return [tok.strip('"') for tok in line.strip().split(" ") if tok]
    raise RuntimeError(f"no cc1 line for {chip}")


def main() -> None:
    src = Path("/tmp/_probe_table.c")
    src.write_text("int f(void){return 0;}\n")
    table = {}
    for chip in CHIPS:
        argv = cc1_argv(chip, src)
        multilib = argv[argv.index("-imultilib") + 1] if "-imultilib" in argv else ""
        flags = [a for a in argv if KEEP.match(a)]
        # The library directory is NOT -print-multi-directory: for avr51 chips
        # that says "avr51" while this toolchain has no avr51 multilib and gcc
        # falls back to the top level. --print-libgcc-file-name is the only
        # answer that matches what the linker actually opens.
        libgcc = subprocess.run(
            [str(GCC), f"-mmcu={chip}", "--print-libgcc-file-name"],
            capture_output=True, text=True).stdout.strip()
        libdir = str(Path(libgcc).resolve().parent.relative_to(
            (TC / "lib" / "gcc" / "avr" / "14.2.0").resolve()))
        libdir = "" if libdir == "." else libdir
        libm = TC / "avr" / "lib" / libdir / "libm.a"
        table[chip] = {"multilib": multilib, "libdir": libdir,
                       "libm_exists": libm.exists(), "flags": flags}
    Path("cc1_flags.json").write_text(json.dumps(table, indent=2) + "\n")

    widths = max(len(c) for c in table)
    for chip, entry in table.items():
        mcu = next(f for f in entry["flags"] if f.startswith("-mmcu="))
        libdir = entry["libdir"] or "(raiz)"
        ok = "ok" if entry["libm_exists"] else "SIN libm.a"
        print(f"{chip:<{widths}}  {mcu:<12} libdir={libdir:<20} {ok}")
    print(f"\n{len(table)} chips -> cc1_flags.json")


if __name__ == "__main__":
    sys.exit(main())
