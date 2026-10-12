"""Regression tests for synthetic engineering realism."""

from collections import defaultdict
from dataclasses import replace

import pytest

from ontologysim.generator.config import (
    MeasurementsConfig,
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.measurements import (
    MeasurementStats,
    iter_measurement_rows,
)
from ontologysim.generator.models import Component
from ontologysim.generator.models import TestResult as ExecutionResult
from ontologysim.generator.pipeline import generate_ground_truth
from ontologysim.generator.scenarios import (
    charging_failure,
    extended_awake,
    software_compatibility,
    stale_navigation,
)
from ontologysim.generator.scenarios.bluetooth_reconnect import CORE_COMPONENTS
from ontologysim.generator.scenarios.registry import SCENARIOS
from ontologysim.generator.scenarios.scenario_components import (
    extend_component_catalog,
)
from ontologysim.generator.scenarios.shared_scenario import (
    ScenarioPlan,
    generate_scenario_ground_truth,
    iter_scenario_log_batches,
)


def _catalog():
    base = [
        Component(
            component_id=cid,
            component_name=name,
            component_type=kind,
            ecu=ecu,
            responsibility=responsibility,
            version="3.4.0",
            status="Active",
            owner_team=team,
        )
        for cid, name, kind, ecu, responsibility, team in CORE_COMPONENTS
    ]
    return extend_component_catalog(base)


@pytest.mark.parametrize(
    ("spec", "pass_bounds", "fail_bounds"),
    [
        (charging_failure.SPEC, (18, 30), (40, 65)),
        (stale_navigation.SPEC, (8, 15), (15, 25)),
        (extended_awake.SPEC, (14, 25), (95, 145)),
        (software_compatibility.SPEC, (10, 25), (10, 25)),
    ],
)
def test_outcome_timeline_fits_scenario_duration(
    spec,
    pass_bounds,
    fail_bounds,
):
    plan = ScenarioPlan(
        seed=20261001,
        requirements=5,
        test_cases=8,
        test_executions=40,
        log_events=450,
        defects=4,
        trace_relationships=100,
    )

    ground_truth = generate_scenario_ground_truth(
        spec,
        plan,
        _catalog(),
    )

    assert len(ground_truth.log_events) == 450

    outcomes = defaultdict(list)
    for log in ground_truth.log_events:
        outcomes[log.execution_id].append(log)

    pass_names = {step.event_type for step in spec.pass_events}
    fail_names = {step.event_type for step in spec.fail_events}

    for execution in ground_truth.test_executions:
        duration = (execution.end_timestamp - execution.start_timestamp).total_seconds()

        failed = execution.result == ExecutionResult.FAIL

        lower, upper = fail_bounds if failed else pass_bounds

        assert lower <= duration <= upper

        logs = outcomes[execution.execution_id]

        assert all(
            execution.start_timestamp <= log.timestamp <= execution.end_timestamp for log in logs
        )

        expected_names = fail_names if failed else pass_names

        late_events = [log for log in logs if log.event_type in expected_names]

        assert len(late_events) == len(expected_names)

        assert (
            min((log.timestamp - execution.start_timestamp).total_seconds() for log in late_events)
            >= 0.69 * duration
        )

    streamed = [
        log
        for batch in iter_scenario_log_batches(
            spec,
            plan,
            ground_truth.test_executions,
            13,
        )
        for log in batch
    ]

    assert streamed == ground_truth.log_events


def test_measurements_consistent_with_executions_and_failures(
    tmp_path,
):
    original = load_generator_config("config/generator.toml")

    config = replace(
        original,
        scenario_name="multi_scenario",
        profile_name="smoke",
        output_dir=tmp_path,
        profile=ProfileConfig(
            requirements=24,
            components=12,
            test_cases=40,
            test_executions=80,
            log_events=800,
            defects=16,
            trace_relationships=160,
        ),
        scenario_weights=tuple((name, 1.0) for name in SCENARIOS),
        measurements=MeasurementsConfig(
            enabled=True,
            samples_per_execution=48,
            missing_sample_rate=0,
            invalid_value_rate=0,
            clock_offset_seconds=0,
        ),
    )

    ground_truth = generate_ground_truth(
        config,
        materialize_logs=False,
    )

    stats = MeasurementStats()
    rows = list(
        iter_measurement_rows(
            ground_truth,
            config,
            stats,
        )
    )

    assert stats.expected_samples == stats.written_samples == 80 * 48

    by_execution = defaultdict(list)

    for row in rows:
        by_execution[row["execution_ref"]].append(row)

    for execution in ground_truth.test_executions:
        prefix = execution.test_case_id.split("-")[1]

        if prefix not in {"CHG", "NAV", "AWAKE", "UPD"}:
            continue

        failed = execution.result == ExecutionResult.FAIL

        series = defaultdict(list)

        for row in by_execution[execution.execution_id]:
            value = row["value_numeric"] if row["value_numeric"] is not None else row["value_text"]
            series[row["signal_name"]].append(value)

        if prefix == "CHG":
            assert all(350 <= value <= 450 for value in series["charging_voltage_v"])

            if failed:
                assert all(value == 0 for value in series["charging_current_a"])
                assert series["charge_state"][-1] == "FAILED"
            else:
                assert max(series["charging_current_a"]) > 0
                assert series["charge_state"][-1] == "CHARGING"

        elif prefix == "NAV":
            if failed:
                assert max(series["gnss_position_age_ms"]) > 5000
            else:
                assert max(series["gnss_position_age_ms"]) < 500

            assert (0.0 in series["gnss_fix_valid"]) == failed

        elif prefix == "AWAKE":
            if failed:
                assert max(series["vehicle_awake_duration_s"]) > 45
            else:
                assert max(series["vehicle_awake_duration_s"]) < 30

            assert ("ASLEEP" in series["vehicle_power_state"]) != failed

        elif prefix == "UPD":
            assert (execution.software_version_hcp3 == "HCP3_3.5.0-B201") == failed

            assert (0.0 in series["interface_compatible"]) == failed

            assert series["software_update_state"][-1] == (
                "INCOMPATIBLE" if failed else "COMPATIBLE"
            )
