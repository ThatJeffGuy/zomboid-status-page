import os
import re

_NAME_RE = re.compile(r"^PublicName=(.*)$", re.MULTILINE)
_PORT_RE = re.compile(r"^DefaultPort=(\d+)$", re.MULTILINE)
_PASSWORD_RE = re.compile(r"^Password=(.*)$", re.MULTILINE)


def read_server_info(ini_path: str | None = None) -> dict:
    path = ini_path or os.environ.get("SERVER_INI", "/run/secrets/server.ini")
    info = {"available": False, "name": None, "port": None, "password": ""}

    if not os.path.exists(path):
        return info
    try:
        with open(path, "r", errors="replace") as f:
            content = f.read()
    except OSError:
        return info

    name_m = _NAME_RE.search(content)
    port_m = _PORT_RE.search(content)
    password_m = _PASSWORD_RE.search(content)

    info["name"] = name_m.group(1).strip() if name_m else None
    info["port"] = int(port_m.group(1)) if port_m else None
    info["password"] = password_m.group(1).strip() if password_m else ""
    info["available"] = info["port"] is not None
    return info
