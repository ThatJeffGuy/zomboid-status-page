import os
import sqlite3


def _path() -> str:
    return os.environ.get("PLAYER_DB", "/run/secrets/player.db")


def total_players(db_path: str | None = None) -> int | None:
    path = db_path or _path()
    if not os.path.exists(path):
        return None
    try:
        con = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=5)
    except sqlite3.Error:
        return None
    try:
        row = con.execute("SELECT COUNT(*) FROM whitelist").fetchone()
        return int(row[0]) if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()
