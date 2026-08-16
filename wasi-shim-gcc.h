#ifndef AVR_WASI_SHIM_GCC_H
#define AVR_WASI_SHIM_GCC_H

#include "wasi-shim.h"

#include <sys/stat.h>

/* gcov-tool's libgcov-util.c walks a directory tree; wasi-libc has no ftw.
   gcov-tool is not part of cc1, so a failing stub is enough to link. */
__attribute__((unused)) static int
ftw (const char *dir, int (*fn) (const char *, const struct stat *, int), int fds)
{
  (void) dir; (void) fn; (void) fds;
  return -1;
}

/* gcc 14's timevar.cc calls times(); wasi-libc declares it but ships no
   implementation. Do NOT include <sys/times.h> here: when configure decides the
   host has no sys/times.h, timevar.cc defines its own `struct tms`, and the
   header's definition then collides with it. A forward declaration is enough
   and works with either. Weak, because wasi-libc's declaration is not static
   and gcc only uses times() for -ftime-report. */
struct tms;

__attribute__((weak)) long
times (struct tms *buf)
{
  (void) buf;
  return 0;
}

#endif
