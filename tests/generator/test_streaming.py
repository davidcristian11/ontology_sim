from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.pipeline import (
    generate_ground_truth,
)
from ontologysim.generator.scenarios.bluetooth_reconnect import (
    iter_bluetooth_log_batches,
)


def test_runtime_logs_are_generated_in_chunks() -> None:
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
        profile=profile,
        chunk_size=100,
    )

    ground_truth = generate_ground_truth(
        config,
        materialize_logs=False,
    )

    assert ground_truth.log_events == []

    batches = list(
        iter_bluetooth_log_batches(
            config,
            ground_truth.test_executions,
            config.chunk_size,
        )
    )

    assert sum(len(batch) for batch in batches) == 600

    assert all(len(batch) <= 100 for batch in batches)


def test_chunk_size_does_not_change_runtime_output(
    tmp_path,
) -> None:
    from dataclasses import replace

    from ontologysim.generator.pipeline import (
        generate_dataset,
    )

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

    first_config = replace(
        config,
        profile=profile,
        profile_name="chunk_50",
        chunk_size=50,
        output_dir=tmp_path,
    )

    second_config = replace(
        config,
        profile=profile,
        profile_name="chunk_137",
        chunk_size=137,
        output_dir=tmp_path,
    )

    first = generate_dataset(first_config)

    second = generate_dataset(second_config)

    assert first.source_counts == second.source_counts

    for relative_path in (
        "runtime/hcp3/hcp3_runtime.dlt",
        "runtime/hcp5/hcp5_runtime.log",
        "runtime/conmod/conmod_runtime.jsonl",
    ):
        first_bytes = (first.output_dir / relative_path).read_bytes()

        second_bytes = (second.output_dir / relative_path).read_bytes()

        assert first_bytes == second_bytes
