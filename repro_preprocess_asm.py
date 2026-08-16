"""Minimal reproducer: AvrgasToolchain._preprocess_asm is not idempotent.

_org_to_bytes multiplies every numeric .org operand by 2 (AVRA word addresses ->
GNU AS byte addresses). Applying it twice doubles again, so the interrupt vector
table is silently stretched from 4-byte slots to 8-byte slots. Nothing fails: the
file still assembles, still links, and produces firmware whose vectors point at
the wrong addresses.

    PYTHONPATH=~/Repos/pymcu-avr/src/python:~/Repos/pymcu-sdk/src/python \
        python repro_preprocess_asm.py
"""

from __future__ import annotations

import re

from rich.console import Console

from pymcu.toolchain.avr.avrgas import AvrgasToolchain

# An ATmega328P vector table as pymcuc emits it: word-addressed .org, one JMP
# per slot. Only the first four slots, enough to show the drift.
RAW = """\
.equ RAMSTART = 0x0100
.org 0x0
	JMP	main
.org 0x2
	JMP	__bad_interrupt
.org 0x4
	JMP	__bad_interrupt
.org 0x6
	JMP	__bad_interrupt
main:
	RJMP	main
__bad_interrupt:
	RJMP	__bad_interrupt
"""


def orgs(text: str) -> list[str]:
    return re.findall(r"^\s*\.org\s+(\S+)", text, re.MULTILINE)


def main() -> None:
    tc = AvrgasToolchain(Console(), chip="atmega328p")

    once = tc._preprocess_asm(RAW, has_jmp=True)
    twice = tc._preprocess_asm(once, has_jmp=True)
    thrice = tc._preprocess_asm(twice, has_jmp=True)

    print("entrada (direcciones de palabra) :", orgs(RAW))
    print("1 pasada  (correcto, bytes)      :", orgs(once))
    print("2 pasadas (MAL, x2 otra vez)     :", orgs(twice))
    print("3 pasadas                        :", orgs(thrice))
    print()
    print("idempotente:", once == twice)
    print()
    print("Separacion entre vectores, en bytes:")
    for label, text in (("1 pasada", once), ("2 pasadas", twice)):
        values = [int(v, 0) for v in orgs(text)]
        deltas = [b - a for a, b in zip(values, values[1:])]
        print(f"  {label:<10} {deltas}   <- el JMP de AVR ocupa 4 bytes")
    print()
    print("El resto de transformaciones si son idempotentes; solo .org se dobla:")
    for name, sample in (
        (".equ", ".equ FOO = 1\n"),
        ("high()", "	LDI	r30, high(main)\n"),
        ("RCALL", "	RCALL	main\n"),
        ("hi8(x*2)", "	LDI	r30, hi8(main * 2)\n"),
    ):
        a = tc._preprocess_asm(sample, has_jmp=True)
        b = tc._preprocess_asm(a, has_jmp=True)
        print(f"  {name:<10} idempotente={a == b}")


if __name__ == "__main__":
    main()
