"""
PC side of the replies sent by the Pico.

  port 5006: recognized sentence as text
  port 5007: audio answer files in packets "FILE:<id>:<seq>:<total>:" + 512 bytes
             (16 kHz, mono, unsigned 8-bit)

Compared with the old version:
  - prints a line when a file starts to arrive
  - if UDP packets are LOST, it says how many and still plays the answer
    (a lost packet becomes a short gap of silence instead of no sound at all)
  - bigger receive buffer
While an answer is playing a file called "mute_mic" exists, so that listen.py
sends silence to the Pico instead of the speaker sound.
"""
import os
import socket
import threading
import time
import wave

UDP_IP = "0.0.0.0"
EVENT_PORT = 5006
AUDIO_PORT = 5007
FS = 16000
CHUNK = 512
STALE_S = 1.5            # a file is finished (or lost) when no packet arrives for this long
SILENCE = b"\x80"        # silence in unsigned 8-bit audio


def parse_packet(data):
    """-> (file_id, seq, total, payload) or None."""
    head = data[:64]
    if not head.startswith(b"FILE:"):
        return None
    parts = head.split(b":", 4)          # FILE, id, seq, total, rest
    if len(parts) < 5:
        return None
    try:
        file_id = parts[1].decode()
        seq = int(parts[2])
        total = int(parts[3])
    except ValueError:
        return None
    header_len = len(b":".join(parts[:4])) + 1
    return file_id, seq, total, data[header_len:]


def play(file_id, audio):
    temp_wav = f"temp_{file_id}.wav"
    with wave.open(temp_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(1)               # unsigned 8-bit
        wf.setframerate(FS)
        wf.writeframes(audio)

    open("mute_mic", "w").close()        # mute the microphone while the answer plays
    os.system(f"mpv --no-video --really-quiet {temp_wav}")
    if os.path.exists("mute_mic"):
        os.remove("mute_mic")
    if os.path.exists(temp_wav):
        os.remove(temp_wav)


def finish(file_id, entry):
    total = entry["total"]
    chunks = entry["chunks"]
    missing = [i for i in range(total) if i not in chunks]
    audio = b"".join(chunks.get(i, SILENCE * CHUNK) for i in range(total))

    if missing:
        print(f"WARNING {file_id}: lost {len(missing)} of {total} packets "
              f"(first missing: {missing[:5]}). Playing with gaps.")
    else:
        print(f"Received complete audio for: {file_id}")
    play(file_id, audio)


def audio_receiver():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1 << 20)
    sock.bind((UDP_IP, AUDIO_PORT))
    sock.settimeout(0.5)
    print(f"Listening for audio packets on port {AUDIO_PORT}...")

    files = {}                           # file_id -> {"total", "chunks", "last"}
    while True:
        try:
            data, _ = sock.recvfrom(2048)
        except socket.timeout:
            data = None

        now = time.time()
        if data is not None:
            parsed = parse_packet(data)
            if parsed:
                file_id, seq, total, payload = parsed
                entry = files.get(file_id)
                if entry is None or seq in entry["chunks"]:
                    # first packet of a new transfer (or the same file sent again)
                    entry = {"total": total, "chunks": {}, "last": now}
                    files[file_id] = entry
                    print(f"Receiving {file_id}: {total} packets...")
                entry["chunks"][seq] = payload
                entry["last"] = now

        for file_id in list(files):
            entry = files[file_id]
            complete = len(entry["chunks"]) == entry["total"]
            stale = now - entry["last"] > STALE_S
            if complete or stale:
                finish(file_id, files.pop(file_id))


threading.Thread(target=audio_receiver, daemon=True).start()

# --- main loop: recognized text ---
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, EVENT_PORT))
print(f"Listening for events from Pico on port {EVENT_PORT}...")

while True:
    data, addr = sock.recvfrom(1024)
    text = data.decode("utf-8", errors="replace")
    print(f"\nReceived from Pico: [{text}]")
