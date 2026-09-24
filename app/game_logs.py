import glob
import os


def _logs_dir() -> str:
    return os.environ.get("LOGS_DIR", "/data/pz-logs")


def find_current(suffix: str, logs_dir: str | None = None) -> str | None:
    pattern = os.path.join(logs_dir or _logs_dir(), f"*_{suffix}.txt")
    matches = glob.glob(pattern)
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)
