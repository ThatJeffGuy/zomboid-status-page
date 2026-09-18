import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from app import game_logs

_LOG_TZ = ZoneInfo("America/Toronto")

_CHAT_MSG_RE = re.compile(
    r"^\[(\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.\d+\]\[info\] "
    r"Got message:ChatMessage\{chat=(\w+), author='([^']*)', text='(.*)'\}\.$"
)
_BROADCAST_RE = re.compile(
    r"^\[(\d{2})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})\.\d+\] "
    r"Server alert message: '(.*)' sent\.\.$"
)


def _parse_ts(dd: str, mm: str, yy: str, hh: str, mi: str, ss: str) -> str:
    year = 2000 + int(yy)
    dt = datetime(year, int(mm), int(dd), int(hh), int(mi), int(ss), tzinfo=_LOG_TZ)
    return dt.isoformat()


def read_recent(limit: int = 50) -> list[dict]:
    path = game_logs.find_current("chat")
    if path is None:
        return []
    try:
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()
    except OSError:
        return []

    messages = []
    for line in lines:
        line = line.rstrip("\n")
        m = _CHAT_MSG_RE.match(line)
        if m:
            dd, mm, yy, hh, mi, ss, _chat, author, text = m.groups()
            messages.append({
                "author": author,
                "text": text,
                "at": _parse_ts(dd, mm, yy, hh, mi, ss),
            })
            continue
        m = _BROADCAST_RE.match(line)
        if m:
            dd, mm, yy, hh, mi, ss, text = m.groups()
            messages.append({
                "author": None,
                "text": text,
                "at": _parse_ts(dd, mm, yy, hh, mi, ss),
            })

    return messages[-limit:]
