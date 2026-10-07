from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.pipeline import generate_ground_truth
from ontologysim.generator.projections import project_all_sources


def _generate_small_dataset():
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

    config = replace(config, profile=profile)

    return generate_ground_truth(config)


def test_projection_preserves_record_counts() -> None:
    ground_truth = _generate_small_dataset()
    projected = project_all_sources(ground_truth)

    assert len(projected["requirements"]) == 12
    assert len(projected["architecture"]["components"]) == 12
    assert len(projected["architecture"]["ecus"]) == 3
    assert len(projected["test_management"]) == 12
    assert len(projected["test_execution"]) == 30
    assert len(projected["defects"]) == len(ground_truth.defects)
    assert len(projected["traces"]) == 80

    runtime_count = (
        len(projected["hcp3_logs"]) + len(projected["hcp5_logs"]) + len(projected["conmod_logs"])
    )

    assert runtime_count == 600


def test_component_identity_differs_between_sources() -> None:
    ground_truth = _generate_small_dataset()
    projected = project_all_sources(ground_truth)

    architecture_components = projected["architecture"]["components"]

    architecture_bt = next(
        record for record in architecture_components if record["component_id"] == "SWC-HCP3-BT-001"
    )

    hcp3_bt = next(
        record for record in projected["hcp3_logs"] if record["component_name"] == "BT_CONN_MGR"
    )

    defect_bt = projected["defects"][0]

    assert architecture_bt["component_name"] == "BluetoothConnectionManager"
    assert hcp3_bt["component_name"] == "BT_CONN_MGR"
    assert defect_bt["affected_component"] == "BT reconnect module"


def test_runtime_sources_use_different_timestamp_formats() -> None:
    ground_truth = _generate_small_dataset()
    projected = project_all_sources(ground_truth)

    hcp3_timestamp = projected["hcp3_logs"][0]["timestamp"]
    hcp5_timestamp = projected["hcp5_logs"][0]["timestamp"]
    conmod_timestamp = projected["conmod_logs"][0]["timestamp"]

    assert "T" not in hcp3_timestamp
    assert "." in hcp5_timestamp
    assert conmod_timestamp.endswith("Z")
