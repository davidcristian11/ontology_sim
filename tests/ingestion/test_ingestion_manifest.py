import pytest

from ontologysim.ingestion.manifest import (
    get_expected_source_count,
    validate_manifest_identity,
)


def test_manifest_identity_and_source_count() -> None:
    manifest = {
        "generation_id": "abc123",
        "profile": "dev",
        "source_counts": {
            "test_management": 1005,
        },
    }

    validate_manifest_identity(
        manifest,
        generation_id="abc123",
        profile="dev",
    )

    assert get_expected_source_count(manifest, "test_management") == 1005


def test_manifest_identity_rejects_wrong_generation() -> None:
    manifest = {
        "generation_id": "abc123",
        "profile": "dev",
        "source_counts": {},
    }

    with pytest.raises(ValueError, match="Generation ID"):
        validate_manifest_identity(
            manifest,
            generation_id="wrong",
            profile="dev",
        )