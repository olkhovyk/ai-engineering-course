import os
from pathlib import Path

from src.env import load_project_env


def test_load_project_env_loads_key_value_file_without_overriding_existing_values():
    env_path = Path("results") / "test.env"
    env_path.parent.mkdir(exist_ok=True)
    env_path.write_text(
        """
        OPENROUTER_API_KEY=from-file
        OPENROUTER_ROUTER_MODEL=mistralai/mistral-nemo
        """,
        encoding="utf-8",
    )

    old_key = os.environ.get("OPENROUTER_API_KEY")
    old_model = os.environ.get("OPENROUTER_ROUTER_MODEL")
    os.environ["OPENROUTER_API_KEY"] = "existing"
    os.environ.pop("OPENROUTER_ROUTER_MODEL", None)

    try:
        loaded = load_project_env(env_path)

        assert loaded is True
        assert os.environ["OPENROUTER_API_KEY"] == "existing"
        assert os.environ["OPENROUTER_ROUTER_MODEL"] == "mistralai/mistral-nemo"
    finally:
        if old_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = old_key

        if old_model is None:
            os.environ.pop("OPENROUTER_ROUTER_MODEL", None)
        else:
            os.environ["OPENROUTER_ROUTER_MODEL"] = old_model
