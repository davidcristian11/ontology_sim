import math
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ProfileConfig:
    requirements: int
    components: int
    test_cases: int
    test_executions: int
    log_events: int
    defects: int
    trace_relationships: int


@dataclass(frozen=True, slots=True)
class BluetoothScenarioConfig:
    failure_rate: float
    defect_probability_given_failure: float


@dataclass(frozen=True, slots=True)
class QualityConfig:
    missing_link_rate: float
    duplicate_record_rate: float
    missing_field_rate: float
    malformed_log_rate: float
    stale_id_rate: float
    free_text_reference_rate: float


@dataclass(frozen=True, slots=True)
class ClockDriftConfig:
    hcp3: float
    hcp5: float
    conmod: float


@dataclass(frozen=True, slots=True)
class GeneratorConfig:
    seed: int
    profile_name: str
    scenario_name: str
    output_dir: Path
    chunk_size: int
    profile: ProfileConfig
    bluetooth_scenario: BluetoothScenarioConfig
    quality: QualityConfig
    clock_drift: ClockDriftConfig
    scenario_weights: tuple[tuple[str, float], ...] = ()


def _validate_probability(name: str, value: float) -> None:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0.0 and 1.0, got {value}")


def _validate_positive(name: str, value: int) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0, got {value}")


def load_generator_config(path: str | Path) -> GeneratorConfig:
    config_path = Path(path)

    if not config_path.exists():
        raise FileNotFoundError(f"Generator config not found: {config_path}")

    with config_path.open("rb") as file:
        raw = tomllib.load(file)

    generator = raw["generator"]
    profile_name = generator["profile"]
    profile_raw = raw["profiles"][profile_name]

    scenario_raw = raw["scenario"]["bluetooth_reconnect"]
    quality_raw = raw["quality"]
    clock_drift_raw = quality_raw["clock_drift_seconds"]

    profile = ProfileConfig(
        requirements=profile_raw["requirements"],
        components=profile_raw["components"],
        test_cases=profile_raw["test_cases"],
        test_executions=profile_raw["test_executions"],
        log_events=profile_raw["log_events"],
        defects=profile_raw["defects"],
        trace_relationships=profile_raw["trace_relationships"],
    )

    bluetooth_scenario = BluetoothScenarioConfig(
        failure_rate=scenario_raw["failure_rate"],
        defect_probability_given_failure=(scenario_raw["defect_probability_given_failure"]),
    )

    quality = QualityConfig(
        missing_link_rate=quality_raw["missing_link_rate"],
        duplicate_record_rate=quality_raw["duplicate_record_rate"],
        missing_field_rate=quality_raw["missing_field_rate"],
        malformed_log_rate=quality_raw["malformed_log_rate"],
        stale_id_rate=quality_raw["stale_id_rate"],
        free_text_reference_rate=quality_raw["free_text_reference_rate"],
    )

    clock_drift = ClockDriftConfig(
        hcp3=float(clock_drift_raw["hcp3"]),
        hcp5=float(clock_drift_raw["hcp5"]),
        conmod=float(clock_drift_raw["conmod"]),
    )

    _validate_positive(
        "chunk_size",
        generator["chunk_size"],
    )

    for field_name in (
        "requirements",
        "components",
        "test_cases",
        "test_executions",
        "log_events",
        "defects",
        "trace_relationships",
    ):
        _validate_positive(
            field_name,
            getattr(profile, field_name),
        )

    _validate_probability(
        "failure_rate",
        bluetooth_scenario.failure_rate,
    )

    _validate_probability(
        "defect_probability_given_failure",
        bluetooth_scenario.defect_probability_given_failure,
    )

    for field_name in (
        "missing_link_rate",
        "duplicate_record_rate",
        "missing_field_rate",
        "malformed_log_rate",
        "stale_id_rate",
        "free_text_reference_rate",
    ):
        _validate_probability(
            field_name,
            getattr(quality, field_name),
        )

    # V2: optional scenario distribution.
    raw_weights = raw.get(
        "scenario_distribution",
        {},
    ).get("weights", {})

    if not isinstance(raw_weights, dict):
        raise TypeError("scenario_distribution.weights must be a TOML table")

    weights: list[tuple[str, float]] = []

    for name, value in sorted(raw_weights.items()):
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"Invalid weight for {name}: {value!r}")

        weights.append((name, float(value)))

    if generator["scenario"] == "multi_scenario" and (
        not weights or sum(weight for _, weight in weights) <= 0
    ):
        raise ValueError("multi_scenario requires positive scenario weights")

    return GeneratorConfig(
        seed=generator["seed"],
        profile_name=profile_name,
        scenario_name=generator["scenario"],
        output_dir=Path(generator["output_dir"]),
        chunk_size=generator["chunk_size"],
        profile=profile,
        bluetooth_scenario=bluetooth_scenario,
        quality=quality,
        clock_drift=clock_drift,
        scenario_weights=tuple(weights),
    )
