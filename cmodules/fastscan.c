/*
 * VoidEye · cmodules/fastscan.c
 * Fast TCP port scanner using non-blocking connect with select().
 *
 * Compile:
 *   gcc -O2 -shared -fPIC -o fastscan.so fastscan.c
 */

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/select.h>
#include <netdb.h>
#include <arpa/inet.h>

#define CONNECT_TIMEOUT_MS 1500

/*
 * scan_port - Test if a single TCP port is open.
 *
 * Returns:
 *   1  if port is OPEN
 *   0  if port is CLOSED / FILTERED
 *  -1  on error
 */
int scan_port(const char *host, int port) {
    struct addrinfo hints, *res;
    char            port_str[8];
    int             sockfd, flags, ret;
    fd_set          fds;
    struct timeval  tv;

    memset(&hints, 0, sizeof(hints));
    hints.ai_family   = AF_UNSPEC;
    hints.ai_socktype = SOCK_STREAM;

    snprintf(port_str, sizeof(port_str), "%d", port);

    if (getaddrinfo(host, port_str, &hints, &res) != 0)
        return -1;

    sockfd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    if (sockfd < 0) { freeaddrinfo(res); return -1; }

    /* set non-blocking */
    flags = fcntl(sockfd, F_GETFL, 0);
    fcntl(sockfd, F_SETFL, flags | O_NONBLOCK);

    ret = connect(sockfd, res->ai_addr, res->ai_addrlen);
    freeaddrinfo(res);

    if (ret == 0) {
        close(sockfd);
        return 1;   /* immediate connect (localhost) */
    }

    if (errno != EINPROGRESS) { close(sockfd); return 0; }

    FD_ZERO(&fds);
    FD_SET(sockfd, &fds);
    tv.tv_sec  = CONNECT_TIMEOUT_MS / 1000;
    tv.tv_usec = (CONNECT_TIMEOUT_MS % 1000) * 1000;

    ret = select(sockfd + 1, NULL, &fds, NULL, &tv);
    close(sockfd);

    if (ret == 1) {
        int       err    = 0;
        socklen_t optlen = sizeof(err);
        getsockopt(sockfd, SOL_SOCKET, SO_ERROR, &err, &optlen);
        return (err == 0) ? 1 : 0;
    }
    return 0;   /* timeout = filtered/closed */
}

/*
 * scan_ports_range - Scan a range of ports.
 *
 * Results written to out_buf as comma-separated list of open ports.
 * Returns number of open ports found.
 */
int scan_ports_range(const char *host, int start_port, int end_port,
                     char *out_buf, int buf_size) {
    int  open_count = 0;
    int  pos        = 0;
    char tmp[16];

    memset(out_buf, 0, buf_size);

    for (int p = start_port; p <= end_port; p++) {
        if (scan_port(host, p) == 1) {
            int n = snprintf(tmp, sizeof(tmp), "%s%d",
                             open_count > 0 ? "," : "", p);
            if (pos + n < buf_size - 1) {
                memcpy(out_buf + pos, tmp, n);
                pos += n;
            }
            open_count++;
        }
    }
    return open_count;
}
