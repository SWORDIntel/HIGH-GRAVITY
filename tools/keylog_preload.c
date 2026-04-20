/*
 * keylog_preload.c — LD_PRELOAD component of HG TLS keylog
 *
 * Job: open the keylog file and build a minimal Go io.Writer struct,
 * then export the two pointer values (itab ptr + data ptr) to
 * /tmp/hg_writer_ptrs so that bpftrace can read them and call
 * bpf_probe_write_user() to plant them into tls.Config.KeyLogWriter
 * just before each writeKeyLog call site.
 *
 * NO binary patching. NO mprotect. NO code injection.
 * Just two 8-byte pointers written to /tmp/hg_writer_ptrs.
 *
 * Compile:
 *   gcc -shared -fPIC -O0 -o tools/keylog_preload.so tools/keylog_preload.c -ldl
 * Install:
 *   sudo bash tools/install_keylog_wrapper.sh
 */
#define _GNU_SOURCE
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <stdlib.h>

#define KEYLOG_PATH "/tmp/hg_tls.keys"
#define PTRS_PATH   "/tmp/hg_writer_ptrs"

/*
 * Go io.Writer interface value = { itab_ptr, data_ptr }
 *
 * itab layout (two uint64s):
 *   [0]  type ptr  — unused by the Write dispatch, set to 0
 *   [8]  Write fn  — pointer to our hg_write_fn
 *
 * Our Write(p []byte)(n int, err error) uses Go register ABI:
 *   In:  RAX = receiver (*int64 fd), RBX = buf ptr, RCX = buf len
 *   Out: RAX = n written, RBX = 0 (nil error)
 */

static void __attribute__((naked)) hg_write_fn(void) {
    __asm__ volatile (
        "push  %rbp\n"
        "mov   %rsp,  %rbp\n"
        "mov   (%rax), %rdi\n"   /* fd  = *receiver  */
        "mov   %rbx,   %rsi\n"   /* buf              */
        "mov   %rcx,   %rdx\n"   /* len              */
        "mov   $1,     %eax\n"   /* SYS_write        */
        "syscall\n"
        "xor   %ebx,   %ebx\n"   /* err = nil        */
        "pop   %rbp\n"
        "ret\n"
    );
}

static uint64_t g_itab[2];   /* { 0, &hg_write_fn }  */
static int64_t  g_fd;        /* open fd               */

__attribute__((constructor))
static void hg_keylog_init(void) {
    const char *path = getenv("HG_KEYLOG_FILE");
    if (!path) path = KEYLOG_PATH;

    int fd = open(path, O_WRONLY|O_CREAT|O_APPEND, 0600);
    if (fd < 0) {
        fprintf(stderr, "[HG] open(%s) failed: %s\n", path, strerror(errno));
        return;
    }

    const char hdr[] = "# NSS SSLKEYLOGFILE\n";
    write(fd, hdr, sizeof(hdr) - 1);

    g_fd      = (int64_t)fd;
    g_itab[0] = 0;
    g_itab[1] = (uint64_t)hg_write_fn;

    /* Export {itab_ptr, data_ptr} for bpftrace */
    int pfd = open(PTRS_PATH, O_WRONLY|O_CREAT|O_TRUNC, 0600);
    if (pfd >= 0) {
        uint64_t ptrs[2] = { (uint64_t)g_itab, (uint64_t)&g_fd };
        write(pfd, ptrs, sizeof(ptrs));
        close(pfd);
    }

    fprintf(stderr, "[HG] keylog init: fd=%d\n", fd);
    fprintf(stderr, "[HG] itab=%p  data=%p\n", (void*)g_itab, (void*)&g_fd);
    fprintf(stderr, "[HG] ptrs -> %s\n", PTRS_PATH);
}
