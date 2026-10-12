import csv
import json
from dataclasses import replace

from openpyxl import load_workbook

from ontologysim.generator.config import ProfileConfig, load_generator_config
from ontologysim.generator.manifest import build_generation_id
from ontologysim.generator.pipeline import generate_dataset, generate_ground_truth
from ontologysim.generator.scenarios.registry import SCENARIOS


def _config(tmp_path, chunk_size):
    original = load_generator_config("config/generator.toml")
    return replace(
        original,
        profile_name="smoke",
        scenario_name="multi_scenario",
        output_dir=tmp_path,
        chunk_size=chunk_size,
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


def test_physical_multi_scenario_pipeline(tmp_path):
    config = _config(tmp_path / "run1", 17)
    result = generate_dataset(config)
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert len(result.files) == 9
    assert manifest["schema_version"] == 2
    assert set(manifest["scenario_statistics"]) == set(SCENARIOS)
    assert result.ground_truth_counts["components"] == 17
    assert result.ground_truth_counts["log_events"] == 800
    assert sum(s["log_events"] for s in manifest["scenario_statistics"].values()) == 800
    assert sum(result.source_counts[x] for x in ("hcp3_logs", "hcp5_logs", "conmod_logs")) >= 800

    with (result.output_dir / "test_management/test_cases.csv").open(encoding="utf-8") as f:
        cases = list(csv.DictReader(f))

    assert len({c["test_steps"] for c in cases}) == 8
    assert {c["test_case_id"].split("-", 2)[1] for c in cases} == {
        "BT",
        "NET",
        "CHG",
        "START",
        "NAV",
        "AWAKE",
        "UPD",
        "POOR",
    }
    assert next(c for c in cases if c["test_case_id"].startswith("TC-BT-"))["preconditions"] == (
        "Vehicle sleeping; paired Bluetooth device available"
    )
    assert all(c["component_refs"] for c in cases)
    assert manifest["configuration"]["scenario_weights"] == dict(config.scenario_weights)

    with (result.output_dir / "test_execution/test_executions.jsonl").open(encoding="utf-8") as f:
        executions = [json.loads(line) for line in f]
    assert len({e["execution_id"] for e in executions}) == 80
    assert all(e["session_id"] for e in executions)

    no_logs = generate_ground_truth(config, materialize_logs=False)
    assert no_logs.log_events == []
    assert len(no_logs.incidents) == 80


def test_physical_output_is_chunk_independent(tmp_path):
    first = generate_dataset(_config(tmp_path / "a", 17))
    second = generate_dataset(_config(tmp_path / "b", 41))

    for file_a in first.files:
        relative = file_a.relative_to(first.output_dir)
        file_b = second.output_dir / relative
        if relative.suffix == ".xlsx":
            workbook_a = load_workbook(file_a, read_only=True)
            workbook_b = load_workbook(file_b, read_only=True)
            assert list(workbook_a.active.values) == list(workbook_b.active.values)
            workbook_a.close()
            workbook_b.close()
        else:
            assert file_a.read_bytes() == file_b.read_bytes(), relative

    manifest_a = json.loads(first.manifest_path.read_text())
    manifest_b = json.loads(second.manifest_path.read_text())
    assert manifest_a["generation_id"] == manifest_b["generation_id"]
    assert manifest_a["scenario_statistics"] == manifest_b["scenario_statistics"]


def test_multi_fingerprint_includes_distribution(tmp_path):
    config = _config(tmp_path, 17)
    altered = replace(
        config,
        scenario_weights=tuple(
            (name, (2.0 if i == 0 else 1.0)) for i, name in enumerate(SCENARIOS)
        ),
    )
    assert build_generation_id(config) != build_generation_id(altered)
