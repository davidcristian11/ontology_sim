from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.models import TestResult as ExecutionResult
from ontologysim.generator.pipeline import generate_ground_truth


def test_bluetooth_scenario_generates_expected_structure() -> None:
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

    # Explicitly select V1 Bluetooth mode, independent of the
    # default scenario configured in generator.toml.
    config = replace(
        config,
        scenario_name="bluetooth_reconnect_after_wake",
        profile=profile,
    )

    ground_truth = generate_ground_truth(config)

    assert len(ground_truth.requirements) == 12
    assert len(ground_truth.components) == 12
    assert len(ground_truth.test_cases) == 12
    assert len(ground_truth.test_executions) == 30
    assert len(ground_truth.log_events) == 600
    assert len(ground_truth.traces) == 80
    assert len(ground_truth.incidents) == 30

    failed = [
        execution
        for execution in ground_truth.test_executions
        if execution.result == ExecutionResult.FAIL
    ]

    assert failed

    failed_execution_ids = {execution.execution_id for execution in failed}

    failure_events = {
        log.execution_id
        for log in ground_truth.log_events
        if log.event_type == "BT_RECONNECT_TIMEOUT"
    }

    assert failure_events == failed_execution_ids
