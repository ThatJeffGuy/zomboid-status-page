import os
from dataclasses import dataclass


@dataclass
class WorldBackend:
    slug: str
    rcon_host: str
    rcon_port: int
    rcon_pass_file: str
    server_ini: str
    events_dir: str
    logs_dir: str
    player_db: str
    caretaking_log: str
    container: str
    content_subdir: str | None


def _main() -> WorldBackend:
    return WorldBackend(
        slug="main",
        rcon_host=os.environ.get("RCON_HOST", "127.0.0.1"),
        rcon_port=int(os.environ.get("RCON_PORT", "27015")),
        rcon_pass_file=os.environ.get("RCON_PASS_FILE", "/run/secrets/pz-rcon"),
        server_ini=os.environ.get("SERVER_INI", "/run/secrets/server.ini"),
        events_dir=os.environ.get("EVENTS_DIR", "/data/pz-storms"),
        logs_dir=os.environ.get("LOGS_DIR", "/data/pz-logs"),
        player_db=os.environ.get("PLAYER_DB", "/run/secrets/player.db"),
        caretaking_log=os.environ.get("CARETAKING_LOG", "/data/pz-caretaking.log"),
        container=os.environ.get("PZ_GAME_CONTAINER", "zomboid-server"),
        content_subdir=None,
    )


def _second() -> WorldBackend | None:
    rcon_port = os.environ.get("SECOND_RCON_PORT")
    if not rcon_port:
        return None
    return WorldBackend(
        slug="second",
        rcon_host=os.environ.get("SECOND_RCON_HOST", "127.0.0.1"),
        rcon_port=int(rcon_port),
        rcon_pass_file=os.environ.get("SECOND_RCON_PASS_FILE", "/run/secrets/pz-rcon"),
        server_ini=os.environ.get("SECOND_SERVER_INI", "/run/secrets/second-server.ini"),
        events_dir=os.environ.get("SECOND_EVENTS_DIR", "/data/second-pz-storms"),
        logs_dir=os.environ.get("SECOND_LOGS_DIR", "/data/second-pz-logs"),
        player_db=os.environ.get("SECOND_PLAYER_DB", "/data/second-pz-db/YourSecondServerName.db"),
        caretaking_log=os.environ.get("SECOND_CARETAKING_LOG", "/data/second-pz-caretaking.log"),
        container=os.environ.get("SECOND_GAME_CONTAINER", "zomboid-server-2"),
        content_subdir="second",
    )


def all_backends() -> dict[str, WorldBackend]:
    backends = {"main": _main()}
    second = _second()
    if second is not None:
        backends["second"] = second
    return backends


def get_backend(slug: str) -> WorldBackend | None:
    return all_backends().get(slug)
