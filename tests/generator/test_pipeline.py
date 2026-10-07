from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.pipeline import generate_dataset


def test_pipeline_generates_complete_dataset(
    tmp_path,
) -> None:
    config = load_generator_config("config/generator.toml")

    profile = ProfileConfig(
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
        profile_name="test",
        profile=profile,
        output_dir=tmp_path,
    )

    summary = generate_dataset(config)

    assert summary.output_dir == tmp_path / "test"
    assert len(summary.files) == 9
    assert summary.total_bytes > 0

    assert summary.ground_truth_counts["requirements"] == 12
    assert summary.ground_truth_counts["test_executions"] == 30
    assert summary.ground_truth_counts["log_events"] == 600

    for path in summary.files:
        assert path.exists()
        assert path.stat().st_size > 0
