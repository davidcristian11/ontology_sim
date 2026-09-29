import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    execution_mode: str
    data_dir: Path


def load_settings(config_path: Path) -> Settings:
    with config_path.open("rb") as file:
        config = tomllib.load(file)

    return Settings(
        execution_mode=config["execution"]["mode"],
        data_dir=Path(config["paths"]["data_dir"]),
    )
