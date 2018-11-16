
import socket

addrs = socket.getaddrinfo(socket.gethostname(),None)

for item in addrs:
    print(item)