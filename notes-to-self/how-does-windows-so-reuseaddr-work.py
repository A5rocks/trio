# There are some tables here:
#   https://web.archive.org/web/20120206195747/https://msdn.microsoft.com/en-us/library/windows/desktop/ms740621(v=vs.85).aspx
# They appear to be wrong.
#
# See https://github.com/python-trio/trio/issues/928 for details and context

import errno
import socket

modes = ["default", "SO_REUSEADDR", "SO_EXCLUSIVEADDRUSE"]
bind_types = ["wildcard", "specific"]


def sock(mode):
    s = socket.socket(family=socket.AF_INET)
    if mode == "SO_REUSEADDR":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    elif mode == "SO_EXCLUSIVEADDRUSE":
        s.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
    return s


def bind(sock, bind_type):
    if bind_type == "wildcard":
        sock.bind(("0.0.0.0", 12345))
    elif bind_type == "specific":
        sock.bind(("127.0.0.1", 12345))
    else:
        raise AssertionError()


def table_entry(mode1, bind_type1, mode2, bind_type2):
    with sock(mode1) as sock1:
        bind(sock1, bind_type1)
        try:
            with sock(mode2) as sock2:
                bind(sock2, bind_type2)
        except OSError as exc:
            if exc.winerror == errno.WSAEADDRINUSE:
                return "INUSE"
            elif exc.winerror == errno.WSAEACCES:
                return "ACCESS"
            raise
        else:
            return "Success"


print(
    """
                                                       second bind
                               | """
    + " | ".join(f"{mode:<19}" for mode in modes),
)

print("""                              """, end="")
for _ in modes:
    print(
        " | " + " | ".join(f"{bind_type:>8}" for bind_type in bind_types),
        end="",
    )

print(
    """
first bind                     -----------------------------------------------------------------""",
    #            default | wildcard |    INUSE |  Success |   ACCESS |  Success |    INUSE |  Success
)

for mode1 in modes:
    for bind_type1 in bind_types:
        row = []
        for mode2 in modes:
            for bind_type2 in bind_types:
                entry = table_entry(mode1, bind_type1, mode2, bind_type2)
                row.append(entry)
                # print(mode1, bind_type1, mode2, bind_type2, entry)
        print(
            f"{mode1:>19} | {bind_type1:>8} | "
            + " | ".join(f"{entry:>8}" for entry in row),
        )
