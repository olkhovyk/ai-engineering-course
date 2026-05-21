from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]


def load_project_env(env_path: str | Path | None = None) -> bool:
    path = Path(env_path) if env_path is not None else BASE_DIR / ".env"
    if not path.exists():
        return False

    try:
        from dotenv import load_dotenv

        load_dotenv(path, override=False)
    except ModuleNotFoundError:
        _load_env_manually(path)

    return True


def _load_env_manually(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
