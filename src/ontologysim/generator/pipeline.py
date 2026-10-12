from dataclasses import dataclass
from pathlib import Path

from ontologysim.generator.config import GeneratorConfig
from ontologysim.generator.corruption import (
    apply_controlled_messiness,
    apply_runtime_messiness,
)
from ontologysim.generator.manifest import (
    write_generation_manifest,
)
from ontologysim.generator.measurements import (
    write_measurements,
)
from ontologysim.generator.models import GroundTruth, LogEvent
from ontologysim.generator.projections import project_all_sources
from ontologysim.generator.scenarios.bluetooth_reconnect import (
    generate_bluetooth_reconnect_ground_truth,
    iter_bluetooth_log_batches,
)
from ontologysim.generator.scenarios.coordinator import (
    BLUETOOTH,
    HANDOVER,
    SHARED_SPECS,
    MultiScenarioResult,
    build_multi_scenario_ground_truth,
    iter_multi_scenario_log_batches,
)
from ontologysim.generator.validation import validate_written_files
from ontologysim.generator.writers import (
    write_runtime_sources,
    write_static_sources,
)

BLUETOOTH_SCENARIO = BLUETOOTH
MULTI_SCENARIO = "multi_scenario"


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    profile_name: str
    output_dir: Path
    ground_truth_counts: dict[str, int]
    source_counts: dict[str, int]
    files: tuple[Path, ...]
    manifest_path: Path
    total_bytes: int


def generate_ground_truth(
    config: GeneratorConfig,
    *,
    materialize_logs: bool = True,
) -> GroundTruth:
    if config.scenario_name == BLUETOOTH_SCENARIO:
        return generate_bluetooth_reconnect_ground_truth(
            config,
            materialize_logs=materialize_logs,
        )

    if config.scenario_name == MULTI_SCENARIO:
        return build_multi_scenario_ground_truth(
            config,
            materialize_logs=materialize_logs,
        ).ground_truth

    raise ValueError(f"Unsupported generator scenario: {config.scenario_name}")


def generate_dataset(
    config: GeneratorConfig,
) -> GenerationSummary:
    multi_result: MultiScenarioResult | None = None

    if config.scenario_name == MULTI_SCENARIO:
        multi_result = build_multi_scenario_ground_truth(
            config,
            materialize_logs=False,
        )
        ground_truth = multi_result.ground_truth
        log_batches = iter_multi_scenario_log_batches(multi_result, config.chunk_size)
    else:
        ground_truth = generate_ground_truth(
            config,
            materialize_logs=False,
        )
        log_batches = iter_bluetooth_log_batches(
            config,
            ground_truth.test_executions,
            config.chunk_size,
        )

    projected = project_all_sources(ground_truth)
    messy_static = apply_controlled_messiness(projected, config)

    output_dir = config.output_dir / config.profile_name
    static_files = write_static_sources(messy_static, output_dir)

    runtime_counts = {
        "hcp3_logs": 0,
        "hcp5_logs": 0,
        "conmod_logs": 0,
    }

    runtime_files: list[Path] = []
    first_batch = True
    total_clean_logs = 0

    scenario_log_counts: dict[str, int] = {}
    expected_event_prefixes: dict[str, str] = {}
    execution_scenarios: dict[str, str] = {}
    execution_sessions: dict[str, str] = {}
    component_ids: set[str] = set()

    if multi_result is not None:
        scenario_log_counts = {run.scenario_id: 0 for run in multi_result.runs}

        expected_event_prefixes = {
            BLUETOOTH: "LOG-",
            HANDOVER: "LOG-NH-",
            **{scenario_id: f"LOG-{spec.prefix}-" for scenario_id, spec in SHARED_SPECS.items()},
        }

        component_ids = {component.component_id for component in ground_truth.components}

        for run in multi_result.runs:
            for execution in run.ground_truth.test_executions:
                execution_scenarios[execution.execution_id] = run.scenario_id

                execution_sessions[execution.execution_id] = execution.session_id

    for log_batch in log_batches:
        total_clean_logs += len(log_batch)

        if multi_result is not None:
            _validate_multi_runtime_batch(
                log_batch,
                component_ids=component_ids,
                execution_scenarios=execution_scenarios,
                execution_sessions=execution_sessions,
                expected_event_prefixes=expected_event_prefixes,
                scenario_log_counts=scenario_log_counts,
            )

        batch_ground_truth = GroundTruth(
            components=ground_truth.components,
            log_events=log_batch,
        )

        projected_batch = project_all_sources(batch_ground_truth)

        messy_batch = apply_runtime_messiness(projected_batch, config)

        runtime_files = write_runtime_sources(
            messy_batch,
            output_dir,
            append=not first_batch,
        )
        first_batch = False

        for source_name in runtime_counts:
            runtime_counts[source_name] += _list_size(messy_batch[source_name])

    if total_clean_logs != config.profile.log_events:
        raise ValueError(
            f"Expected {config.profile.log_events} clean log events; generated {total_clean_logs}"
        )

    scenario_statistics: dict[str, dict[str, int]] | None = None

    if multi_result is not None:
        scenario_statistics = {}

        for run in multi_result.runs:
            scenario_id = run.scenario_id
            expected = multi_result.allocations["log_events"][scenario_id]
            actual = scenario_log_counts[scenario_id]

            if actual != expected:
                raise ValueError(
                    f"{scenario_id}: expected {expected} log events; generated {actual}"
                )

            scenario_statistics[scenario_id] = {
                "requirements": len(run.ground_truth.requirements),
                "test_cases": len(run.ground_truth.test_cases),
                "test_executions": len(run.ground_truth.test_executions),
                "log_events": actual,
                "defects": len(run.ground_truth.defects),
                "traces": len(run.ground_truth.traces),
                "incidents": len(run.ground_truth.incidents),
            }

    written_files = static_files + runtime_files

    source_counts = _source_counts(messy_static)
    source_counts.update(runtime_counts)

    measurement_statistics: dict[str, object] | None = None

    # Explicit V2 opt-in.
    # Bluetooth-only V1 remains unchanged.
    if multi_result is not None and config.measurements.enabled:
        measurement_file, measurement_stats = write_measurements(ground_truth, config, output_dir)

        expected_measurements = (
            len(ground_truth.test_executions) * config.measurements.samples_per_execution
        )

        if measurement_stats.expected_samples != expected_measurements:
            raise ValueError("Measurement count invariant failed")

        if (
            measurement_stats.written_samples + measurement_stats.missing_samples
            != measurement_stats.expected_samples
        ):
            raise ValueError("Measurement quality accounting mismatch")

        written_files.append(measurement_file)

        source_counts["measurements"] = measurement_stats.written_samples

        measurement_statistics = measurement_stats.as_manifest()

    validate_written_files(written_files)

    ground_truth_counts = _ground_truth_counts(
        ground_truth,
        total_clean_logs,
    )

    total_bytes = sum(path.stat().st_size for path in written_files)

    manifest_path = write_generation_manifest(
        config=config,
        output_dir=output_dir,
        ground_truth_counts=ground_truth_counts,
        source_counts=source_counts,
        files=written_files,
        total_bytes=total_bytes,
        scenario_statistics=scenario_statistics,
        measurement_statistics=measurement_statistics,
    )

    return GenerationSummary(
        profile_name=config.profile_name,
        output_dir=output_dir,
        ground_truth_counts=ground_truth_counts,
        source_counts=source_counts,
        files=tuple(written_files),
        manifest_path=manifest_path,
        total_bytes=total_bytes,
    )


def _validate_multi_runtime_batch(
    events: list[LogEvent],
    *,
    component_ids: set[str],
    execution_scenarios: dict[str, str],
    execution_sessions: dict[str, str],
    expected_event_prefixes: dict[str, str],
    scenario_log_counts: dict[str, int],
) -> None:
    for event in events:
        scenario_id = execution_scenarios.get(event.execution_id)

        if scenario_id is None:
            raise ValueError(f"Unknown execution in log event: {event.execution_id}")

        if event.component_id not in component_ids:
            raise ValueError(f"Unknown component in log event: {event.component_id}")

        if event.session_id != execution_sessions[event.execution_id]:
            raise ValueError(f"Wrong session in log event: {event.event_id}")

        sequence = scenario_log_counts[scenario_id] + 1
        expected_id = f"{expected_event_prefixes[scenario_id]}{sequence:09d}"

        if event.event_id != expected_id:
            raise ValueError(f"Unexpected log event ID: {event.event_id}; expected {expected_id}")

        scenario_log_counts[scenario_id] = sequence


def _ground_truth_counts(
    ground_truth: GroundTruth,
    log_event_count: int,
) -> dict[str, int]:
    return {
        "requirements": len(ground_truth.requirements),
        "components": len(ground_truth.components),
        "test_cases": len(ground_truth.test_cases),
        "test_executions": len(ground_truth.test_executions),
        "log_events": log_event_count,
        "defects": len(ground_truth.defects),
        "traces": len(ground_truth.traces),
        "incidents": len(ground_truth.incidents),
    }


def _source_counts(
    sources: dict[str, object],
) -> dict[str, int]:
    architecture = sources["architecture"]

    if not isinstance(architecture, dict):
        raise TypeError("architecture must be a dictionary")

    components = architecture["components"]

    if not isinstance(components, list):
        raise TypeError("architecture components must be a list")

    return {
        "requirements": _list_size(sources["requirements"]),
        "components": len(components),
        "test_management": _list_size(sources["test_management"]),
        "test_execution": _list_size(sources["test_execution"]),
        "hcp3_logs": 0,
        "hcp5_logs": 0,
        "conmod_logs": 0,
        "defects": _list_size(sources["defects"]),
        "traces": _list_size(sources["traces"]),
    }


def _list_size(value: object) -> int:
    if not isinstance(value, list):
        raise TypeError("Expected source projection to be a list")
    return len(value)
