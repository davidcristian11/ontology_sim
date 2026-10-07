from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.pipeline import generate_ground_truth


def test_same_seed_produces_same_ground_truth() -> None:
    config = load_generator_config("config/generator.toml")

    small_profile = ProfileConfig(
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
        profile=small_profile,
    )

    first = generate_ground_truth(config)
    second = generate_ground_truth(config)

    assert first == second
