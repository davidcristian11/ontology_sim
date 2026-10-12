from dataclasses import replace

from ontologysim.generator.config import ProfileConfig, load_generator_config
from ontologysim.generator.projections.hcp3_logs import project_hcp3_logs
from ontologysim.generator.projections.test_execution import project_test_executions
from ontologysim.generator.scenarios.bluetooth_reconnect import (
    generate_bluetooth_reconnect_ground_truth,
)
from ontologysim.generator.scenarios.coordinator import build_multi_scenario_ground_truth
from ontologysim.generator.scenarios.registry import SCENARIOS


def _small_config():
    config = load_generator_config("config/generator.toml")
    return replace(
        config,
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
    )


def test_v1_source_metadata_is_unchanged():
    config = replace(_small_config(), scenario_name="bluetooth_reconnect_after_wake")
    ground_truth = generate_bluetooth_reconnect_ground_truth(config, materialize_logs=True)

    hcp3 = project_hcp3_logs(ground_truth)
    executions = project_test_executions(ground_truth)

    assert hcp3
    assert all(row["context_id"] == "BT" for row in hcp3)
    assert all(row["application_id"] == "INFOTAINMENT" for row in hcp3)
    assert all(row["executor"] == "automated_bt_regression" for row in executions)


def test_multi_scenario_uses_component_context_and_suite_executor():
    result = build_multi_scenario_ground_truth(
        replace(_small_config(), scenario_name="multi_scenario"),
        materialize_logs=True,
    )

    ground_truth = result.ground_truth
    hcp3 = project_hcp3_logs(ground_truth)
    executions = project_test_executions(ground_truth)

    assert {row["test_case_id"].split("-")[1] for row in executions} == {
        "BT",
        "NET",
        "CHG",
        "START",
        "NAV",
        "AWAKE",
        "UPD",
        "POOR",
    }

    assert {row["executor"] for row in executions} == {
        "automated_bt_regression",
        "automated_connectivity_regression",
        "automated_charging_regression",
        "automated_startup_regression",
        "automated_navigation_regression",
        "automated_power_management_regression",
        "automated_software_compatibility",
        "automated_connectivity_stress",
    }

    bluetooth_rows = [
        row
        for row in hcp3
        if row["_ontology_sim_event_id"].startswith("LOG-")
        and row["_ontology_sim_event_id"][4:].isdigit()
    ]

    assert bluetooth_rows
    assert all(row["context_id"] == "BT" for row in bluetooth_rows)

    assert any(row["context_id"] == "CONNECTIVITY" for row in hcp3)
    assert any(row["context_id"] == "STARTUP" for row in hcp3)
    assert any(row["context_id"] == "NAVIGATION" for row in hcp3)
    assert any(row["context_id"] == "MEDIA" for row in hcp3)
    assert any(row["context_id"] == "UPDATE" for row in hcp3)

    non_bluetooth_rows = [row for row in hcp3 if row not in bluetooth_rows]

    assert non_bluetooth_rows
    assert all(row["context_id"] != "BT" for row in non_bluetooth_rows)

    assert set(hcp3[0]) == {
        "_ontology_sim_event_id",
        "timestamp",
        "ecu_id",
        "application_id",
        "context_id",
        "component_name",
        "severity",
        "event_type",
        "message",
        "session_id",
        "execution_id",
        "software_version",
        "thread_id",
    }

    assert set(executions[0]) == {
        "execution_id",
        "test_case_id",
        "campaign_id",
        "session_id",
        "start_timestamp",
        "end_timestamp",
        "duration_ms",
        "result",
        "execution_environment",
        "vehicle_id",
        "software_version_hcp3",
        "software_version_hcp5",
        "software_version_conmod",
        "hardware_configuration",
        "executor",
        "failure_reason",
        "log_refs",
        "measurement_refs",
    }
