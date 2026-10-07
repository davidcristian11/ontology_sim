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
from ontologysim.generator.models import GroundTruth
from ontologysim.generator.projections import (
    project_all_sources,
)
from ontologysim.generator.scenarios.bluetooth_reconnect import (
    generate_bluetooth_reconnect_ground_truth,
    iter_bluetooth_log_batches,
)
from ontologysim.generator.validation import (
    validate_written_files,
)
from ontologysim.generator.writers import (
    write_runtime_sources,
    write_static_sources,
)

BLUETOOTH_SCENARIO = "bluetooth_reconnect_after_wake"


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

    raise ValueError(f"Unsupported generator scenario: {config.scenario_name}")


def generate_dataset(
    config: GeneratorConfig,
) -> GenerationSummary:
    ground_truth = generate_ground_truth(
        config,
        materialize_logs=False,
    )

    projected = project_all_sources(ground_truth)

    messy_static = apply_controlled_messiness(
        projected,
        config,
    )

    output_dir = config.output_dir / config.profile_name

    static_files = write_static_sources(
        messy_static,
        output_dir,
    )

    runtime_counts = {
        "hcp3_logs": 0,
        "hcp5_logs": 0,
        "conmod_logs": 0,
    }

    runtime_files: list[Path] = []

    first_batch = True

    for log_batch in iter_bluetooth_log_batches(
        config,
        ground_truth.test_executions,
        config.chunk_size,
    ):
        batch_ground_truth = GroundTruth(
            components=ground_truth.components,
            log_events=log_batch,
        )

        projected_batch = project_all_sources(batch_ground_truth)

        messy_batch = apply_runtime_messiness(
            projected_batch,
            config,
        )

        runtime_files = write_runtime_sources(
            messy_batch,
            output_dir,
            append=not first_batch,
        )

        first_batch = False

        for source_name in runtime_counts:
            records = messy_batch[source_name]

            if not isinstance(
                records,
                list,
            ):
                raise TypeError(f"{source_name} must be a list")

            runtime_counts[source_name] += len(records)

    written_files = static_files + runtime_files

    validate_written_files(written_files)

    source_counts = _source_counts(messy_static)

    source_counts.update(runtime_counts)

    ground_truth_counts = _ground_truth_counts(
        ground_truth,
        config.profile.log_events,
    )

    total_bytes = sum(path.stat().st_size for path in written_files)

    manifest_path = write_generation_manifest(
        config=config,
        output_dir=output_dir,
        ground_truth_counts=(ground_truth_counts),
        source_counts=source_counts,
        files=written_files,
        total_bytes=total_bytes,
    )

    return GenerationSummary(
        profile_name=config.profile_name,
        output_dir=output_dir,
        ground_truth_counts=(ground_truth_counts),
        source_counts=source_counts,
        files=tuple(written_files),
        manifest_path=manifest_path,
        total_bytes=total_bytes,
    )


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

    if not isinstance(
        architecture,
        dict,
    ):
        raise TypeError("architecture must be a dictionary")

    components = architecture["components"]

    if not isinstance(
        components,
        list,
    ):
        raise TypeError("architecture components must be a list")

    return {
        "requirements": _list_size(sources["requirements"]),
        "components": len(components),
        "test_management": (_list_size(sources["test_management"])),
        "test_execution": (_list_size(sources["test_execution"])),
        "hcp3_logs": 0,
        "hcp5_logs": 0,
        "conmod_logs": 0,
        "defects": _list_size(sources["defects"]),
        "traces": _list_size(sources["traces"]),
    }


def _list_size(
    value: object,
) -> int:
    if not isinstance(
        value,
        list,
    ):
        raise TypeError("Expected source projection to be a list")

    return len(value)
