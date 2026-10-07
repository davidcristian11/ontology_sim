import json
from dataclasses import replace

from ontologysim.generator.config import (
    load_generator_config,
)
from ontologysim.generator.manifest import (
    build_generation_id,
)
from ontologysim.generator.pipeline import (
    generate_dataset,
)


def test_pipeline_writes_generation_manifest(
    tmp_path,
) -> None:
    config = load_generator_config("config/generator.toml")

    small_profile = replace(
        config.profile,
        requirements=12,
        components=12,
        test_cases=12,
        test_executions=30,
        log_events=600,
        defects=3,
        trace_relationships=80,
    )

    config = replace(
        config,
        profile_name="manifest_test",
        profile=small_profile,
        output_dir=tmp_path,
        chunk_size=100,
    )

    summary = generate_dataset(config)

    assert summary.manifest_path.exists()

    manifest = json.loads(summary.manifest_path.read_text(encoding="utf-8"))

    assert manifest["profile"] == ("manifest_test")
    assert manifest["scenario"] == (config.scenario_name)
    assert manifest["seed"] == (config.seed)

    assert manifest["ground_truth_counts"] == summary.ground_truth_counts

    assert manifest["source_counts"] == summary.source_counts

    assert manifest["total_size_bytes"] == summary.total_bytes

    for file_info in manifest["files"]:
        path = summary.output_dir / file_info["path"]

        assert path.exists()
        assert path.stat().st_size == file_info["size_bytes"]

    other_chunk_size = replace(
        config,
        chunk_size=137,
    )

    assert build_generation_id(config) == build_generation_id(other_chunk_size)
