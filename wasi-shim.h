#ifndef AVR_WASI_SHIM_H
#define AVR_WASI_SHIM_H

__attribute__((unused)) static char *
mktemp (char *tmpl)
{
  static unsigned int counter = 0;
  __SIZE_TYPE__ len = __builtin_strlen (tmpl);
  if (len < 6)
    {
      if (len)
        tmpl[0] = '\0';
      return tmpl;
    }
  char *x = tmpl + len - 6;
  unsigned int v = ++counter * 2654435761u + (unsigned int) (__SIZE_TYPE__) tmpl;
  static const char cs[] = "abcdefghijklmnopqrstuvwxyz0123456789";
  for (int i = 0; i < 6; i++)
    {
      x[i] = cs[v % 36];
      v /= 36;
    }
  return tmpl;
}

#define AVR_WASI_ENOSYS_STUB(name, ret, params)                               \
  __attribute__((unused)) static ret name params                              \
  {                                                                           \
    return (ret) -1;                                                          \
  }

AVR_WASI_ENOSYS_STUB (fork, int, (void))
AVR_WASI_ENOSYS_STUB (wait, int, (int *status))
AVR_WASI_ENOSYS_STUB (pipe, int, (int fds[2]))
AVR_WASI_ENOSYS_STUB (dup, int, (int fd))
AVR_WASI_ENOSYS_STUB (dup2, int, (int a, int b))
AVR_WASI_ENOSYS_STUB (kill, int, (int pid, int sig))
AVR_WASI_ENOSYS_STUB (execv, int, (const char *p, char *const *a))
AVR_WASI_ENOSYS_STUB (execvp, int, (const char *p, char *const *a))
AVR_WASI_ENOSYS_STUB (execve, int, (const char *p, char *const *a, char *const *e))

#undef AVR_WASI_ENOSYS_STUB

__attribute__((unused)) static unsigned int
umask (unsigned int mask)
{
  (void) mask;
  return 0022;
}

#endif
