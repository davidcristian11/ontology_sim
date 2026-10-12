from pathlib import Path

from ontologysim.generator.config import (
    BluetoothScenarioConfig,
    ClockDriftConfig,
    GeneratorConfig,
    ProfileConfig,
    QualityConfig,
)
from ontologysim.generator.scenarios.coordinator import (
    build_multi_scenario_ground_truth,
    iter_multi_scenario_log_batches,
)
from ontologysim.generator.scenarios.registry import SCENARIOS


def _config() -> GeneratorConfig:
    return GeneratorConfig(
        seed=20261001,
        profile_name="smoke",
        scenario_name="multi_scenario",
        output_dir=Path("data/generated_v2"),
        chunk_size=17,
        profile=ProfileConfig(
            requirements=24,
            components=12,
            test_cases=40,
            test_executions=80,
            log_events=800,
            defects=16,
            trace_relationships=160,
        ),
        bluetooth_scenario=BluetoothScenarioConfig(
            failure_rate=0.12,
            defect_probability_given_failure=0.17,
        ),
        quality=QualityConfig(
            missing_link_rate=0.03,
            duplicate_record_rate=0.005,
            missing_field_rate=0.01,
            malformed_log_rate=0.002,
            stale_id_rate=0.01,
            free_text_reference_rate=0.05,
        ),
        clock_drift=ClockDriftConfig(
            hcp3=1.5,
            hcp5=-0.8,
            conmod=0.3,
        ),
        scenario_weights=tuple((scenario_id, 1.0) for scenario_id in SCENARIOS),
    )


def test_coordinator_combines_eight_scenarios() -> None:
    result = build_multi_scenario_ground_truth(
        _config(),
        materialize_logs=False,
    )

    ground_truth = result.ground_truth

    assert len(result.runs) == 8
    assert len(ground_truth.components) == 17
    assert len(ground_truth.requirements) == 24
    assert len(ground_truth.test_cases) == 40
    assert len(ground_truth.test_executions) == 80
    assert len(ground_truth.incidents) == 80
    assert len(ground_truth.traces) == 160
    assert ground_truth.log_events == []

    assert {incident.scenario for incident in ground_truth.incidents} == set(SCENARIOS)

    assert all(
        sum(allocation.values()) == getattr(_config().profile, field_name)
        for field_name, allocation in result.allocations.items()
    )


def test_coordinator_is_deterministic() -> None:
    config = _config()

    first = build_multi_scenario_ground_truth(config)
    second = build_multi_scenario_ground_truth(config)

    assert first.ground_truth == second.ground_truth
    assert first.allocations == second.allocations


def test_combined_streaming_is_chunk_independent() -> None:
    config = _config()

    materialized = build_multi_scenario_ground_truth(
        config,
        materialize_logs=True,
    )

    no_logs = build_multi_scenario_ground_truth(
        config,
        materialize_logs=False,
    )

    for chunk_size in (17, 43):
        batches = list(
            iter_multi_scenario_log_batches(
                no_logs,
                chunk_size,
            )
        )

        assert all(len(batch) <= chunk_size for batch in batches)

        events = [event for batch in batches for event in batch]

        assert len(events) == 800
        assert events == materialized.ground_truth.log_events
