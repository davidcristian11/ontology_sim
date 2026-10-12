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
from ontologysim.generator.pipeline import (
    generate_dataset,
    generate_ground_truth,
)
from ontologysim.generator.scenarios.registry import SCENARIOS


def _config(
    tmp_path,
    *,
    chunk_size=17,
    missing=0.02,
    invalid=0.01,
):
    base = load_generator_config("config/generator.toml")

    return replace(
        base,
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
        measurements=MeasurementsConfig(
            enabled=True,
            samples_per_execution=48,
            missing_sample_rate=missing,
            invalid_value_rate=invalid,
            clock_offset_seconds=1.0,
        ),
    )


def test_measurement_references_and_accounting(tmp_path):
    config = _config(tmp_path)

    ground_truth = generate_ground_truth(config, materialize_logs=False)

    stats = MeasurementStats()
    rows = list(iter_measurement_rows(ground_truth, config, stats))

    executions = {execution.execution_id: execution for execution in ground_truth.test_executions}

    assert stats.expected_samples == 80 * 48
    assert len(rows) == stats.written_samples

    assert stats.written_samples + stats.missing_samples == stats.expected_samples

    assert len({row["measurement_id"] for row in rows}) == len(rows)

    assert len(stats.signals) >= 11

    for row in rows:
        assert "component_id" not in row
        assert "scenario_id" not in row

        execution = executions[row["execution_ref"]]

        assert row["session_ref"] == execution.session_id
        assert row["ecu_id"] in ("HCP3", "HCP5", "ConMod")
        assert row["component_ref"]

        assert (row["value_numeric"] is None) != (row["value_text"] is None)


def test_measurements_deterministic_and_chunk_independent(
    tmp_path,
):
    first = _config(
        tmp_path / "first",
        chunk_size=17,
    )
    second = _config(
        tmp_path / "second",
        chunk_size=41,
    )

    a_gt = generate_ground_truth(first, materialize_logs=False)
    b_gt = generate_ground_truth(second, materialize_logs=False)

    a_stats = MeasurementStats()
    b_stats = MeasurementStats()

    a = list(iter_measurement_rows(a_gt, first, a_stats))
    b = list(iter_measurement_rows(b_gt, second, b_stats))

    assert a == b
    assert a_stats.as_manifest() == b_stats.as_manifest()


def test_invalid_measurements_are_deliberately_detectable(
    tmp_path,
):
    config = _config(
        tmp_path,
        missing=0.0,
        invalid=1.0,
    )

    ground_truth = generate_ground_truth(config, materialize_logs=False)

    stats = MeasurementStats()
    rows = list(iter_measurement_rows(ground_truth, config, stats))

    assert stats.missing_samples == 0
    assert stats.invalid_values == len(rows)

    assert all(
        row["value_numeric"] == -999.0 or row["value_text"] == "INVALID_STATE" for row in rows
    )


def test_parquet_contract_and_manifest(tmp_path):
    import json

    parquet = pytest.importorskip("pyarrow.parquet")

    config = _config(tmp_path)
    result = generate_dataset(config)

    assert len(result.files) == 10
    assert "measurements" in result.source_counts

    path = result.output_dir / "measurements" / "vehicle_signals.parquet"

    table = parquet.read_table(path)

    assert table.num_rows == result.source_counts["measurements"]

    assert table.column_names == [
        "measurement_id",
        "timestamp_utc",
        "execution_ref",
        "session_ref",
        "ecu_id",
        "component_ref",
        "signal_name",
        "value_numeric",
        "value_text",
        "unit",
    ]

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 3

    assert manifest["measurement_statistics"]["written_samples"] == table.num_rows

    assert manifest["measurement_statistics"]["expected_samples"] == 80 * 48


def test_bluetooth_v1_unchanged_when_measurements_opted_in(
    tmp_path,
):
    import json

    config = replace(
        _config(tmp_path),
        scenario_name="bluetooth_reconnect_after_wake",
    )

    result = generate_dataset(config)

    assert len(result.files) == 9
    assert "measurements" not in result.source_counts

    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert manifest["schema_version"] == 1
