"""The AVR toolchain as wasm32-wasip1 modules: avr-as, avr-ld, avr-objcopy and
the C/C++ front ends cc1 and cc1plus, plus the libraries and headers they need.

One architecture-independent wheel replaces one native build per platform. It
ships as a single project on purpose: cc1_flags.json has to match the libgcc.a
and the binutils published alongside it, so the pieces could never really carry
independent versions. Requires the `wasmtime` runtime.
"""

from pathlib import Path

__version__ = "0.1.0"

ROOT = Path(__file__).resolve().parent
WASM_DIR = ROOT / "wasm"
SYSROOT_DIR = ROOT / "sysroot"
INCLUDE_DIR = ROOT / "include"
FLAGS_TABLE = ROOT / "cc1_flags.json"

TOOLS = ("avr-as", "avr-ld", "avr-objcopy", "cc1", "cc1plus")


def wasm_module(name: str) -> Path:
    """Path to a tool module, e.g. wasm_module("cc1plus")."""
    path = WASM_DIR / f"{name}.wasm"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def sysroot(multilib: str) -> Path:
    """Path to the libgcc.a / libm.a directory for a library subdirectory.

    Keyed by multilib, not by BFD emulation: attiny13 and attiny85 are both
    avr25 to the linker but need different libgcc.a.
    """
    path = SYSROOT_DIR / multilib if multilib else SYSROOT_DIR
    if not path.is_dir():
        raise FileNotFoundError(path)
    return path
