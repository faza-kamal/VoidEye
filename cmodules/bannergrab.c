/*
 * VoidEye · cmodules/bannergrab.c
 * High-performance TCP banner grabber compiled as shared library.
 *
 * Compile:
 *   gcc -O2 -shared -fPIC -o bannergrab.so bannergrab.c
 *
 * Python integration:
 *   import ctypes
 *   lib = ctypes.CDLL("./cmodules/bannergrab.so")
 *   lib.grab_banner.restype  = ctypes.c_int
 *   lib.grab_banner.argtypes = [ctypes.c_char_p, ctypes.c_int,
 *                               ctypes.c_char_p, ctypes.c_int]
 *   buf = ctypes.create_string_buffer(4096)
 *   ret = lib.grab_banner(b"example.com", 80, buf, 4096)
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netdb.h>
#include <arpa/inet.h>

#define TIMEOUT_SEC  5
#define HTTP_REQUEST "HEAD / HTTP/1.0\r\nConnection: close\r\n\r\n"

/*
 * grab_banner - Connect to host:port and retrieve the server banner.
 *
 * Parameters:
 *   host     - hostname or IP string
 *   port     - TCP port number
 *   out_buf  - caller-allocated buffer to receive banner text
 *   buf_size - size of out_buf
 *
 * Returns:
 *   0  on success  (out_buf contains banner, NUL-terminated)
 *  -1  on failure  (out_buf contains error description)
 */
int grab_banner(const char *host, int port, char *out_buf, int buf_size) {
    struct addrinfo hints, *res, *rp;
    int             sockfd = -1;
    char            port_str[8];
    ssize_t         nbytes;
    struct timeval  tv;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family   = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    snprintf(port_str, sizeof(port_str), "%d", port);

    if (getaddrinfo(host, port_str, &hints, &res) != 0) {
        snprintf(out_buf, buf_size, "ERROR: getaddrinfo failed for %s", host);
        return -1;
    }

    for (rp = res; rp != NULL; rp = rp->ai_next) {
        sockfd = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
        if (sockfd == -1) continue;

        /* set connect timeout */
        tv.tv_sec  = TIMEOUT_SEC;
        tv.tv_usec = 0;
        setsockopt(sockfd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
        setsockopt(sockfd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv));

        if (connect(sockfd, rp->ai_addr, rp->ai_addrlen) == 0)
            break;

        close(sockfd);
        sockfd = -1;
    }
    freeaddrinfo(res);

    if (sockfd == -1) {
        snprintf(out_buf, buf_size, "ERROR: could not connect to %s:%d", host, port);
        return -1;
    }

    /* send HTTP HEAD request to trigger banner */
    if (send(sockfd, HTTP_REQUEST, strlen(HTTP_REQUEST), 0) < 0) {
        snprintf(out_buf, buf_size, "ERROR: send() failed");
        close(sockfd);
        return -1;
    }

    memset(out_buf, 0, buf_size);
    nbytes = recv(sockfd, out_buf, buf_size - 1, 0);
    close(sockfd);

    if (nbytes <= 0) {
        snprintf(out_buf, buf_size, "ERROR: recv() returned %zd", nbytes);
        return -1;
    }

    return 0;
}
