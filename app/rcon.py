import os
import re
import socket
import struct

SERVERDATA_AUTH = 3
SERVERDATA_EXECCOMMAND = 2


class RconError(Exception):
    pass


def _encode(rid: int, typ: int, body: str) -> bytes:
    payload = struct.pack("<ii", rid, typ) + body.encode("utf-8") + b"\x00\x00"
    return struct.pack("<i", len(payload)) + payload


def _recvall(sock: socket.socket, n: int) -> bytes | None:
    buf = b""
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def _decode(sock: socket.socket):
    head = _recvall(sock, 4)
    if not head:
        return None
    (length,) = struct.unpack("<i", head)
    data = _recvall(sock, length)
    if data is None:
        return None
    rid, typ = struct.unpack("<ii", data[:8])
    return rid, typ, data[8:-2].decode("utf-8", "replace")


def exec_command(host: str, port: int, password: str, command: str, timeout: float = 10.0) -> str:
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as e:
        raise RconError(f"connect failed: {e}") from e

    sock.settimeout(timeout)
    with sock:
        sock.sendall(_encode(1, SERVERDATA_AUTH, password))
        reply = _decode(sock)
        if reply and reply[1] == 0:
            reply = _decode(sock)
        if not reply or reply[0] == -1:
            raise RconError("auth failed")

        sock.sendall(_encode(2, SERVERDATA_EXECCOMMAND, command))
        out = []
        while True:
            try:
                pkt = _decode(sock)
            except socket.timeout:
                break
            if pkt is None:
                break
            out.append(pkt[2])
            if len(pkt[2]) < 3700:
                break
        return "".join(out).strip()


_YAML_PASSWORD_RE = re.compile(r'''password:\s*["']?([^"'\n]+?)["']?\s*$''', re.MULTILINE)


def read_password(path: str) -> str:
    with open(path, "r") as f:
        content = f.read()
    m = _YAML_PASSWORD_RE.search(content)
    pw = m.group(1).strip() if m else content.strip()
    if not pw:
        raise RconError(f"{path} is empty")
    return pw


_PLAYER_COUNT_RE = re.compile(r"connected[^(]*\((\d+)\)")
_PLAYER_NAME_RE = re.compile(r"^\s*-\s*(.+?)\s*$", re.MULTILINE)


def parse_player_count(players_output: str) -> int:
    m = _PLAYER_COUNT_RE.search(players_output)
    if m:
        return int(m.group(1))
    names = _PLAYER_NAME_RE.findall(players_output)
    return len(names)


def parse_player_names(players_output: str) -> list[str]:
    return [n for n in _PLAYER_NAME_RE.findall(players_output) if n]


class RconClient:
    def __init__(self, host: str, port: int, password_file: str, timeout: float = 10.0):
        self.host = host
        self.port = port
        self.password_file = password_file
        self.timeout = timeout

    def run(self, command: str) -> str:
        password = read_password(self.password_file)
        return exec_command(self.host, self.port, password, command, self.timeout)

    @classmethod
    def from_env(cls) -> "RconClient":
        return cls(
            host=os.environ.get("RCON_HOST", "127.0.0.1"),
            port=int(os.environ.get("RCON_PORT", "27015")),
            password_file=os.environ.get("RCON_PASS_FILE", "/run/secrets/pz-rcon"),
        )
