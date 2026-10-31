import socket, select, time

socks = []
for port in (5006, 5007):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", port))
    socks.append(s)

counts = {5006: 0, 5007: 0}
end = time.time() + 25
print("Listening 25 s on 5006 and 5007... say 'tell me about yourself' now")
while time.time() < end:
    ready, _, _ = select.select(socks, [], [], 0.5)
    for s in ready:
        data, addr = s.recvfrom(2048)
        counts[s.getsockname()[1]] += 1
print("received:", counts)
