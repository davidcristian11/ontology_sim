import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from ontologysim.generator.config import GeneratorConfig


def build_generation_id(
    config: GeneratorConfig,
) -> str:
    identity = {
        "profile": config.profile_name,
        "scenario": config.scenario_name,
        "seed": config.seed,
        "profile_config": asdict(config.profile),
        "scenario_config": asdict(config.bluetooth_scenario),
        "quality_config": asdict(config.quality),
        "clock_drift": asdict(config.clock_drift),
    }

    payload = json.dumps(
        identity,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()

    return hashlib.sha256(payload).hexdigest()[:16]


def write_generation_manifest(
    *,
    config: GeneratorConfig,
    output_dir: Path,
    ground_truth_counts: dict[str, int],
    source_counts: dict[str, int],
    files: list[Path],
    total_bytes: int,
) -> Path:
    manifest_path = output_dir / "manifest.json"

    manifest = {
        "schema_version": 1,
        "generation_id": build_generation_id(config),
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": config.profile_name,
        "scenario": config.scenario_name,
        "seed": config.seed,
        "configuration": {
            "chunk_size": config.chunk_size,
            "profile": asdict(config.profile),
            "scenario": asdict(config.bluetooth_scenario),
            "quality": asdict(config.quality),
            "clock_drift_seconds": asdict(config.clock_drift),
        },
        "ground_truth_counts": (ground_truth_counts),
        "source_counts": source_counts,
        "files": [
            {
                "path": path.relative_to(output_dir).as_posix(),
                "size_bytes": (path.stat().st_size),
            }
            for path in sorted(
                files,
                key=str,
            )
        ],
        "total_size_bytes": total_bytes,
    }

    manifest_path.write_text(
        json.dumps(
            manifest,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    return manifest_path
