from copy import deepcopy
from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    QualityConfig,
    load_generator_config,
)
from ontologysim.generator.corruption import (
    apply_controlled_messiness,
)
from ontologysim.generator.pipeline import generate_ground_truth
from ontologysim.generator.projections import project_all_sources


def _build_dataset():
    config = load_generator_config("config/generator.toml")

    profile = ProfileConfig(
        requirements=20,
        components=12,
        test_cases=20,
        test_executions=50,
        log_events=1000,
        defects=5,
        trace_relationships=100,
    )

    quality = QualityConfig(
        missing_link_rate=0.20,
        duplicate_record_rate=0.10,
        missing_field_rate=0.20,
        malformed_log_rate=0.10,
        stale_id_rate=0.20,
        free_text_reference_rate=0.20,
    )

    config = replace(
        config,
        profile=profile,
        quality=quality,
    )

    ground_truth = generate_ground_truth(config)
    projected = project_all_sources(ground_truth)

    return config, ground_truth, projected


def test_corruption_is_deterministic() -> None:
    config, _, projected = _build_dataset()

    first = apply_controlled_messiness(
        projected,
        config,
    )

    second = apply_controlled_messiness(
        projected,
        config,
    )

    assert first == second


def test_corruption_does_not_modify_clean_sources() -> None:
    config, ground_truth, projected = _build_dataset()

    original_ground_truth = deepcopy(ground_truth)
    original_projected = deepcopy(projected)

    messy = apply_controlled_messiness(
        projected,
        config,
    )

    assert ground_truth == original_ground_truth
    assert projected == original_projected
    assert messy != projected


def test_corruption_introduces_expected_problems() -> None:
    config, _, projected = _build_dataset()

    messy = apply_controlled_messiness(
        projected,
        config,
    )

    assert len(messy["test_execution"]) > len(projected["test_execution"])

    assert any(record["test_case_id"] is None for record in messy["test_execution"])

    assert any(record["execution_id"] is None for record in messy["hcp3_logs"])

    assert any(record.get("_ontology_sim_malformed") for record in messy["hcp3_logs"])

    assert any(record["trace_status"] == "Broken" for record in messy["traces"])


def test_clock_drift_changes_runtime_timestamps() -> None:
    config, _, projected = _build_dataset()

    messy = apply_controlled_messiness(
        projected,
        config,
    )

    assert messy["hcp3_logs"][0]["timestamp"] != projected["hcp3_logs"][0]["timestamp"]

    assert messy["hcp5_logs"][0]["timestamp"] != projected["hcp5_logs"][0]["timestamp"]

    assert messy["conmod_logs"][0]["timestamp"] != projected["conmod_logs"][0]["timestamp"]
