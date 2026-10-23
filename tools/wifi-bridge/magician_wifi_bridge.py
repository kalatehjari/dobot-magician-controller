#!/usr/bin/env python3
"""Wi-Fi bridge for Magician Smart Controller (Dobot Magician with the Wi-Fi module, "Wireless 2").

The Wi-Fi module takes the arm's usual commands as UDP messages on port 8899, but a web page cannot
send UDP. This small program runs on the same computer as the browser and passes the messages
between the page (a WebSocket on 127.0.0.1, port 8890) and the arm.

    python3 magician_wifi_bridge.py

then, in the app: Setup -> Wireless -> Wi-Fi, type the arm's address and press "Connect over Wi-Fi".
Stop it with Ctrl+C. Standard Python 3.8 or later, nothing to install.

Options:
    --port 8890            the WebSocket port the page connects to
    --arm 192.168.1.50     the arm's address, if the page does not send one
    --allow-origin URL     another web page that may use the bridge (repeatable). Allowed anyway:
                           the app opened from a file, from localhost, and from
                           https://kalatehjari.github.io (the project's website).
Only this computer can reach the bridge (it listens on 127.0.0.1), and only the pages above may use
it, so other websites cannot move your arm.
"""
import argparse, base64, hashlib, ipaddress, select, socket, struct, sys, threading, time, urllib.parse

VERSION = '1.0'
GUID = '258EAFA5-E914-47DA-95CA-C5AB0DC85B11'
SITE_ORIGINS = {'null', 'https://kalatehjari.github.io'}


def say(msg):
    print(time.strftime('%H:%M:%S ') + msg, flush=True)


def origin_ok(origin, extra):
    if origin in SITE_ORIGINS or origin in extra:
        return True
    try:
        host = urllib.parse.urlparse(origin).hostname
    except ValueError:
        return False
    return host in ('localhost', '127.0.0.1', '::1')


def recv_exact(conn, n):
    buf = b''
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError('closed')
        buf += chunk
    return buf


def read_message(conn):
    """One WebSocket message: (opcode, payload). Joins fragments; unmasks."""
    data, first_op = b'', None
    while True:
        b0, b1 = recv_exact(conn, 2)
        fin, op, masked, n = b0 & 0x80, b0 & 0x0F, b1 & 0x80, b1 & 0x7F
        if n == 126:
            n = struct.unpack('>H', recv_exact(conn, 2))[0]
        elif n == 127:
            n = struct.unpack('>Q', recv_exact(conn, 8))[0]
        if n > 1 << 20:
            raise ConnectionError('message too large')
        mask = recv_exact(conn, 4) if masked else b'\0\0\0\0'
        payload = bytes(c ^ mask[i % 4] for i, c in enumerate(recv_exact(conn, n)))
        if op >= 8:                      # control frames may come between fragments
            return op, payload
        if first_op is None:
            first_op = op
        data += payload
        if fin:
            return first_op, data


def send_message(conn, op, payload, lock):
    n = len(payload)
    head = bytes([0x80 | op]) + (bytes([n]) if n < 126 else bytes([126]) + struct.pack('>H', n) if n < 65536 else bytes([127]) + struct.pack('>Q', n))
    with lock:
        conn.sendall(head + payload)


def handle(conn, addr, args):
    try:
        conn.settimeout(10)
        data = b''
        while b'\r\n\r\n' not in data:
            chunk = conn.recv(4096)
            if not chunk or len(data) > 16384:
                return
            data += chunk
        head = data.split(b'\r\n\r\n', 1)[0].decode('latin-1')
        lines = head.split('\r\n')
        parts = lines[0].split(' ')
        path = parts[1] if len(parts) > 1 else '/'
        headers = {}
        for line in lines[1:]:
            if ':' in line:
                k, v = line.split(':', 1)
                headers[k.strip().lower()] = v.strip()
        if headers.get('upgrade', '').lower() != 'websocket':
            body = f'Magician Wi-Fi bridge {VERSION} is running. Connect from the app (Setup -> Wireless -> Wi-Fi).\n'.encode()
            conn.sendall(b'HTTP/1.1 200 OK\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: %d\r\n\r\n' % len(body) + body)
            return
        origin = headers.get('origin', 'null')
        if not origin_ok(origin, set(args.allow_origin)):
            say(f'Refused a connection from the web page {origin} (not the app). Use --allow-origin to allow it.')
            conn.sendall(b'HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\n\r\n')
            return
        q = urllib.parse.parse_qs(urllib.parse.urlparse(path).query)
        arm = (q.get('arm') or [args.arm or ''])[0].strip()
        try:
            arm_port = int((q.get('port') or ['8899'])[0])
            ipaddress.IPv4Address(arm)
        except ValueError:
            say(f'The page asked for the arm at "{arm}", which is not an IPv4 address.')
            conn.sendall(b'HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n')
            return
        key = headers.get('sec-websocket-key', '')
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode()).digest()).decode()
        conn.sendall(('HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n'
                      f'Sec-WebSocket-Accept: {accept}\r\n\r\n').encode())
        conn.settimeout(None)
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        udp.bind(('0.0.0.0', 0))
        lock, stop = threading.Lock(), threading.Event()
        counts = {'to': 0, 'from': 0}
        say(f'App connected ({origin}); passing commands to the arm at {arm}:{arm_port} (UDP).')

        def from_arm():
            while not stop.is_set():
                r, _, _ = select.select([udp], [], [], 0.5)
                if not r:
                    continue
                try:
                    msg, src = udp.recvfrom(4096)
                except OSError:
                    break
                if src[0] != arm:
                    continue
                counts['from'] += 1
                try:
                    send_message(conn, 2, msg, lock)
                except OSError:
                    break

        t = threading.Thread(target=from_arm, daemon=True)
        t.start()
        try:
            while True:
                op, payload = read_message(conn)
                if op == 8:                                   # close
                    try:
                        send_message(conn, 8, payload[:2], lock)
                    except OSError:
                        pass
                    break
                if op == 9:                                   # ping
                    send_message(conn, 10, payload, lock)
                elif op in (1, 2) and payload:
                    udp.sendto(payload, (arm, arm_port))
                    counts['to'] += 1
        except (ConnectionError, OSError):
            pass
        finally:
            stop.set()
            udp.close()
            say(f'App disconnected ({counts["to"]} messages to the arm, {counts["from"]} back).')
    finally:
        try:
            conn.close()
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser(description='Wi-Fi bridge between Magician Smart Controller (browser) and a Dobot Magician Wi-Fi module.')
    ap.add_argument('--port', type=int, default=8890, help='WebSocket port for the app (default 8890)')
    ap.add_argument('--arm', default='', help="the arm's IP address, if the app does not send one")
    ap.add_argument('--allow-origin', action='append', default=[], help='another web page origin that may use the bridge')
    args = ap.parse_args()
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        srv.bind(('127.0.0.1', args.port))
    except OSError as e:
        sys.exit(f'Cannot listen on 127.0.0.1:{args.port} ({e}). Is the bridge already running?')
    srv.listen(4)
    say(f'Magician Wi-Fi bridge {VERSION}: waiting for the app on ws://127.0.0.1:{args.port} (Ctrl+C stops it).')
    try:
        while True:
            conn, addr = srv.accept()
            threading.Thread(target=handle, args=(conn, addr, args), daemon=True).start()
    except KeyboardInterrupt:
        say('Stopped.')


if __name__ == '__main__':
    main()
