from pathlib import Path

from ontologysim.config import load_settings


def test_local_configuration_can_be_loaded():
    settings = load_settings(Path("config/local.toml"))

    assert settings.execution_mode == "local"
    assert settings.data_dir == Path("data")
    assert settings.logging_level == "INFO"
