import glob
import os


def _logs_dir() -> str:
    return os.environ.get("LOGS_DIR", "/data/pz-logs")


def find_current(suffix: str) -> str | None:
    pattern = os.path.join(_logs_dir(), f"*_{suffix}.txt")
    matches = glob.glob(pattern)
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)
