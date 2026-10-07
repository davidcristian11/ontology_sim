import json
from pathlib import Path
from typing import Any


def load_manifest(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as file:
        return json.load(file)


def validate_manifest_identity(
    manifest: dict[str, Any],
    generation_id: str,
    profile: str,
) -> None:
    if manifest["generation_id"] != generation_id:
        raise ValueError("Generation ID does not match")

    if manifest["profile"] != profile:
        raise ValueError("Profile does not match")


def get_expected_source_count(
    manifest: dict[str, Any],
    source_name: str,
) -> int:
    return int(manifest["source_counts"][source_name])