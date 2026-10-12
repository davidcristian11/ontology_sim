"""Streaming source-native measurements for automotive test executions.

No canonical component IDs or hidden scenario IDs are written to Parquet.
"""

import hashlib
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from ontologysim.generator.config import GeneratorConfig
from ontologysim.generator.models import ECU, GroundTruth, TestResult

ROW_GROUP_SIZE = 4096

SIGNALS: dict[str, tuple[tuple[str, str, str], ...]] = {
    "BT": (
        ("battery_current_a", "SWC-HCP5-ENERGY-004", "A"),
        ("vehicle_power_state", "SWC-HCP5-WAKE-002", ""),
        ("cellular_rssi_dbm", "SWC-CON-CELL-002", "dBm"),
    ),
    "NET": (
        ("cellular_rssi_dbm", "SWC-CON-CELL-002", "dBm"),
        ("packet_loss_pct", "SWC-CON-DIAG-003", "%"),
        ("network_state", "SWC-CON-CELL-002", ""),
    ),
    "CHG": (
        ("charging_current_a", "SWC-HCP5-CHG-005", "A"),
        ("charging_voltage_v", "SWC-HCP5-CHG-005", "V"),
        ("battery_current_a", "SWC-HCP5-ENERGY-004", "A"),
        ("charge_state", "SWC-HCP5-CHG-005", ""),
    ),
    "START": (
        ("vehicle_power_state", "SWC-HCP5-STATE-003", ""),
        ("vehicle_awake_duration_s", "SWC-HCP5-WAKE-002", "s"),
    ),
    "NAV": (
        ("gnss_position_age_ms", "SRV-CON-GNSS-005", "ms"),
        ("gnss_fix_valid", "SRV-CON-GNSS-005", "bool"),
        ("cellular_rssi_dbm", "SWC-CON-CELL-002", "dBm"),
    ),
    "AWAKE": (
        ("vehicle_awake_duration_s", "SWC-HCP5-WAKE-002", "s"),
        ("battery_current_a", "SWC-HCP5-ENERGY-004", "A"),
        ("vehicle_power_state", "SWC-HCP5-STATE-003", ""),
    ),
    "UPD": (
        ("interface_compatible", "SWC-HCP3-UPD-007", "bool"),
        ("software_update_state", "SWC-HCP3-UPD-007", ""),
        ("vehicle_power_state", "SWC-HCP5-STATE-003", ""),
    ),
    "POOR": (
        ("cellular_rssi_dbm", "SWC-CON-CELL-002", "dBm"),
        ("packet_loss_pct", "SWC-CON-DIAG-003", "%"),
        ("network_state", "SWC-CON-CELL-002", ""),
    ),
}

SOURCE_COMPONENT_REFS = {
    "SWC-HCP5-ENERGY-004": "ENERGY_SVC",
    "SWC-HCP5-WAKE-002": "WAKE_COORD",
    "SWC-HCP5-STATE-003": "VEHICLE_STATE_SVC",
    "SWC-HCP5-CHG-005": "CHARGE_STATE_MGR",
    "SWC-CON-CELL-002": "CELLULAR_MGR",
    "SWC-CON-DIAG-003": "NETWORK_DIAG",
    "SRV-CON-GNSS-005": "GNSS_SVC",
    "SWC-HCP3-UPD-007": "UPDATE_COMPAT",
}


@dataclass(slots=True)
class MeasurementStats:
    expected_samples: int = 0
    written_samples: int = 0
    missing_samples: int = 0
    invalid_values: int = 0
    signals: dict[str, int] = field(default_factory=dict)

    def as_manifest(self) -> dict[str, object]:
        return {
            "expected_samples": self.expected_samples,
            "written_samples": self.written_samples,
            "missing_samples": self.missing_samples,
            "invalid_values": self.invalid_values,
            "signals": dict(sorted(self.signals.items())),
            "format": "parquet",
            "source_contract": "measurements_v1",
        }


def _selected(
    seed: int,
    namespace: str,
    identifier: str,
    rate: float,
) -> bool:
    if rate <= 0:
        return False

    digest = hashlib.sha256(f"{seed}:{namespace}:{identifier}".encode()).digest()

    return int.from_bytes(digest[:8], "big") / 2**64 < rate


def _value(
    signal: str,
    progress: float,
    failed: bool,
    elapsed_s: float,
    duration_s: float,
    scenario_prefix: str,
) -> tuple[float | None, str | None]:
    """Generate a scenario-consistent clean measurement value.

    Thresholds are synthetic PoC assumptions.
    Charging voltage is measured at the vehicle battery/DC bus.
    """

    if signal == "cellular_rssi_dbm":
        return (
            round(
                (-111 - 7 * progress) if failed else (-82 - 5 * progress),
                2,
            ),
            None,
        )

    if signal == "packet_loss_pct":
        return (
            round(
                (24 + 14 * progress) if failed else (0.5 + progress),
                2,
            ),
            None,
        )

    if signal == "gnss_position_age_ms":
        age_ms = elapsed_s * 1000 if failed else 180 + 120 * progress
        return round(age_ms, 2), None

    if signal == "gnss_fix_valid":
        valid = not (failed and elapsed_s >= 5.0)
        return float(valid), None

    if signal == "charging_current_a":
        if failed or progress < 0.90:
            return 0.0, None

        current = 4.0 + (progress - 0.90) / 0.10 * 14.0
        return round(current, 2), None

    if signal == "charging_voltage_v":
        return (
            round(365.0 + 25.0 * progress, 2),
            None,
        )

    if signal == "vehicle_awake_duration_s":
        if scenario_prefix == "AWAKE" and not failed:
            return (
                round(
                    min(
                        elapsed_s,
                        0.90 * duration_s,
                    ),
                    3,
                ),
                None,
            )

        return round(elapsed_s, 3), None

    if signal == "battery_current_a":
        if scenario_prefix == "CHG":
            if not failed and progress >= 0.90:
                return (
                    round(
                        -12.0 - 6.0 * progress,
                        2,
                    ),
                    None,
                )

            return 0.3, None

        if scenario_prefix == "AWAKE":
            if not failed and progress >= 0.90:
                return 0.03, None

            return (
                round(
                    1.0 + 0.2 * progress,
                    2,
                ),
                None,
            )

        return (
            round(
                (1.5 if failed else 0.2) + progress * 0.1,
                2,
            ),
            None,
        )

    if signal == "interface_compatible":
        compatible = not (failed and progress >= 0.70)
        return float(compatible), None

    if signal == "network_state":
        return (
            None,
            ("DEGRADED" if failed and progress >= 0.35 else "CONNECTED"),
        )

    if signal == "vehicle_power_state":
        if scenario_prefix == "AWAKE" and not failed and progress >= 0.90:
            return None, "ASLEEP"

        return None, "AWAKE"

    if signal == "charge_state":
        if progress < 0.70:
            return None, "PREPARING"

        if failed:
            return (
                None,
                "FAILED" if progress >= 0.90 else "WAITING_FOR_AUTH",
            )

        if progress < 0.90:
            return None, "AUTHORIZED"

        return None, "CHARGING"

    if signal == "software_update_state":
        if progress < 0.90:
            return None, "VALIDATING"

        return (
            None,
            "INCOMPATIBLE" if failed else "COMPATIBLE",
        )

    raise ValueError(f"Unknown measurement signal: {signal}")


def iter_measurement_rows(
    ground_truth: GroundTruth,
    config: GeneratorConfig,
    stats: MeasurementStats,
) -> Iterator[dict[str, object]]:
    """Yield deterministic measurement records."""

    cases = {case.test_case_id: case for case in ground_truth.test_cases}

    components = {component.component_id: component for component in ground_truth.components}

    samples = config.measurements.samples_per_execution
    signal_counts: Counter[str] = Counter()

    for execution in ground_truth.test_executions:
        case = cases[execution.test_case_id]
        prefix = case.test_case_id.split("-", 2)[1]

        if prefix not in SIGNALS:
            raise ValueError(f"No measurement signals for {case.test_case_id}")

        if execution.end_timestamp is None:
            raise ValueError(f"Missing clean end timestamp: {execution.execution_id}")

        duration_s = (execution.end_timestamp - execution.start_timestamp).total_seconds()

        if duration_s <= 0:
            raise ValueError(f"Non-positive execution duration: {execution.execution_id}")

        for index in range(samples):
            signal, component_id, unit = SIGNALS[prefix][index % len(SIGNALS[prefix])]

            component = components[component_id]
            measurement_id = f"M-{execution.execution_id}-{index + 1:05d}"

            stats.expected_samples += 1

            if _selected(
                config.seed,
                "measurement.missing",
                measurement_id,
                config.measurements.missing_sample_rate,
            ):
                stats.missing_samples += 1
                continue

            progress = (index + 1) / (samples + 1)
            elapsed_s = duration_s * progress

            numeric, textual = _value(
                signal,
                progress,
                execution.result != TestResult.PASS,
                elapsed_s,
                duration_s,
                prefix,
            )

            if _selected(
                config.seed,
                "measurement.invalid",
                measurement_id,
                config.measurements.invalid_value_rate,
            ):
                stats.invalid_values += 1

                if numeric is not None:
                    numeric = -999.0
                else:
                    textual = "INVALID_STATE"

            direction = {
                ECU.HCP3: 1.0,
                ECU.HCP5: -1.0,
                ECU.CONMOD: 0.5,
            }[component.ecu]

            clock_offset = (
                direction * config.measurements.clock_offset_seconds * (1 + progress * 0.05)
            )

            timestamp = execution.start_timestamp + timedelta(seconds=elapsed_s + clock_offset)

            stats.written_samples += 1
            signal_counts[signal] += 1

            yield {
                "measurement_id": measurement_id,
                "timestamp_utc": timestamp,
                "execution_ref": execution.execution_id,
                "session_ref": execution.session_id,
                "ecu_id": component.ecu.value,
                "component_ref": (SOURCE_COMPONENT_REFS[component_id]),
                "signal_name": signal,
                "value_numeric": numeric,
                "value_text": textual,
                "unit": unit,
            }

    stats.signals = dict(signal_counts)


def write_measurements(
    ground_truth: GroundTruth,
    config: GeneratorConfig,
    output_dir: Path,
) -> tuple[Path, MeasurementStats]:
    """Write Parquet incrementally using fixed-size row groups."""

    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError("Measurements require pyarrow. Run: uv sync") from error

    schema = pa.schema(
        [
            ("measurement_id", pa.string()),
            (
                "timestamp_utc",
                pa.timestamp("ms", tz="UTC"),
            ),
            ("execution_ref", pa.string()),
            ("session_ref", pa.string()),
            ("ecu_id", pa.string()),
            ("component_ref", pa.string()),
            ("signal_name", pa.string()),
            ("value_numeric", pa.float64()),
            ("value_text", pa.string()),
            ("unit", pa.string()),
        ]
    )

    path = output_dir / "measurements" / "vehicle_signals.parquet"
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = path.with_suffix(".parquet.part")

    stats = MeasurementStats()
    buffer: list[dict[str, object]] = []

    try:
        with pq.ParquetWriter(
            temp_path,
            schema,
            compression="zstd",
        ) as writer:
            for row in iter_measurement_rows(
                ground_truth,
                config,
                stats,
            ):
                buffer.append(row)

                if len(buffer) == ROW_GROUP_SIZE:
                    writer.write_table(
                        pa.Table.from_pylist(
                            buffer,
                            schema=schema,
                        )
                    )
                    buffer.clear()

            if buffer:
                writer.write_table(
                    pa.Table.from_pylist(
                        buffer,
                        schema=schema,
                    )
                )

        if stats.written_samples == 0:
            raise ValueError("No measurements written; lower the missing sample rate")

        temp_path.replace(path)

    finally:
        temp_path.unlink(missing_ok=True)

    return path, stats
