from copy import deepcopy
from datetime import datetime, timedelta

from ontologysim.generator.config import GeneratorConfig
from ontologysim.generator.corruption.common import (
    duplicate_records,
    remove_records,
    select_indices,
    set_field_to_none,
)
from ontologysim.generator.randoms import random_for


def apply_controlled_messiness(
    projected: dict[str, object],
    config: GeneratorConfig,
) -> dict[str, object]:
    sources = deepcopy(projected)

    _corrupt_requirements(sources, config)
    _corrupt_test_management(sources, config)
    _corrupt_test_executions(sources, config)

    _corrupt_hcp3_logs(sources, config)
    _corrupt_hcp5_logs(sources, config)
    _corrupt_conmod_logs(sources, config)

    _corrupt_defects(sources, config)
    _corrupt_traces(sources, config)

    return sources


def _records(
    sources: dict[str, object],
    name: str,
) -> list[dict[str, object]]:
    value = sources[name]

    if not isinstance(value, list):
        raise TypeError(f"Expected source {name!r} to contain a list.")

    return value


def _corrupt_requirements(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "requirements")

    set_field_to_none(
        records,
        "target_component",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.requirements.missing_component",
        ),
    )

    set_field_to_none(
        records,
        "verification_method",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.requirements.missing_field",
        ),
    )

    selected = select_indices(
        len(records),
        config.quality.stale_id_rate,
        random_for(
            config.seed,
            "corruption.requirements.stale_component",
        ),
    )

    for index in selected:
        component = records[index].get("target_component")

        if isinstance(component, str):
            records[index]["target_component"] = f"{component}_Legacy"

    sources["requirements"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.requirements.duplicates",
        ),
    )


def _corrupt_test_management(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "test_management")

    set_field_to_none(
        records,
        "requirement_refs",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.tests.missing_requirement",
        ),
    )

    selected = select_indices(
        len(records),
        config.quality.free_text_reference_rate,
        random_for(
            config.seed,
            "corruption.tests.free_text_requirement",
        ),
    )

    for index in selected:
        requirement_refs = records[index].get("requirement_refs")

        if isinstance(requirement_refs, str) and requirement_refs:
            records[index]["requirement_refs"] = f"See requirement(s): {requirement_refs}"

    set_field_to_none(
        records,
        "preconditions",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.tests.missing_preconditions",
        ),
    )

    sources["test_management"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.tests.duplicates",
        ),
    )


def _corrupt_test_executions(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "test_execution")

    set_field_to_none(
        records,
        "test_case_id",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.executions.missing_test_case",
        ),
    )

    set_field_to_none(
        records,
        "end_timestamp",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.executions.missing_end",
        ),
    )

    sources["test_execution"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.executions.duplicates",
        ),
    )


def _corrupt_hcp3_logs(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "hcp3_logs")

    for record in records:
        timestamp = record["timestamp"]

        if isinstance(timestamp, str):
            record["timestamp"] = _shift_hcp3_timestamp(
                timestamp,
                config.clock_drift.hcp3,
            )

    set_field_to_none(
        records,
        "execution_id",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.hcp3.missing_execution",
        ),
    )

    set_field_to_none(
        records,
        "thread_id",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.hcp3.missing_thread",
        ),
    )

    _mark_malformed(
        records,
        config,
        "hcp3",
    )

    sources["hcp3_logs"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.hcp3.duplicates",
        ),
    )


def _corrupt_hcp5_logs(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "hcp5_logs")

    for record in records:
        timestamp = record["timestamp"]

        if isinstance(timestamp, str):
            record["timestamp"] = _shift_hcp5_timestamp(
                timestamp,
                config.clock_drift.hcp5,
            )

    set_field_to_none(
        records,
        "session_id",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.hcp5.missing_session",
        ),
    )

    set_field_to_none(
        records,
        "execution_id",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.hcp5.missing_execution",
        ),
    )

    _mark_malformed(
        records,
        config,
        "hcp5",
    )

    sources["hcp5_logs"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.hcp5.duplicates",
        ),
    )


def _corrupt_conmod_logs(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "conmod_logs")

    for record in records:
        timestamp = record["timestamp"]

        if isinstance(timestamp, str):
            record["timestamp"] = _shift_conmod_timestamp(
                timestamp,
                config.clock_drift.conmod,
            )

    set_field_to_none(
        records,
        "execution_ref",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.conmod.missing_execution",
        ),
    )

    set_field_to_none(
        records,
        "network_type",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.conmod.missing_network",
        ),
    )

    sources["conmod_logs"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.conmod.duplicates",
        ),
    )


def _corrupt_defects(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "defects")

    set_field_to_none(
        records,
        "test_execution_refs",
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.defects.missing_execution",
        ),
    )

    set_field_to_none(
        records,
        "root_cause",
        config.quality.missing_field_rate,
        random_for(
            config.seed,
            "corruption.defects.missing_root_cause",
        ),
    )

    stale_indices = select_indices(
        len(records),
        config.quality.stale_id_rate,
        random_for(
            config.seed,
            "corruption.defects.stale_component",
        ),
    )

    for index in stale_indices:
        component = records[index].get("affected_component")

        if isinstance(component, str):
            records[index]["affected_component"] = f"{component} legacy"

    free_text_indices = select_indices(
        len(records),
        config.quality.free_text_reference_rate,
        random_for(
            config.seed,
            "corruption.defects.free_text_refs",
        ),
    )

    for index in free_text_indices:
        record = records[index]
        execution_refs = record.get("test_execution_refs")

        if not isinstance(execution_refs, str):
            continue

        if not execution_refs:
            continue

        description = record.get("description")

        if not isinstance(description, str):
            description = ""

        record["description"] = f"{description} Related execution(s): {execution_refs}."

        record["test_execution_refs"] = ""

    sources["defects"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.defects.duplicates",
        ),
    )


def _corrupt_traces(
    sources: dict[str, object],
    config: GeneratorConfig,
) -> None:
    records = _records(sources, "traces")

    records = remove_records(
        records,
        config.quality.missing_link_rate,
        random_for(
            config.seed,
            "corruption.traces.missing",
        ),
    )

    stale_indices = select_indices(
        len(records),
        config.quality.stale_id_rate,
        random_for(
            config.seed,
            "corruption.traces.stale_ids",
        ),
    )

    for index in stale_indices:
        target_id = records[index].get("target_id")

        if isinstance(target_id, str):
            records[index]["target_id"] = f"{target_id}-STALE"

        records[index]["trace_status"] = "Broken"

    sources["traces"] = duplicate_records(
        records,
        config.quality.duplicate_record_rate,
        random_for(
            config.seed,
            "corruption.traces.duplicates",
        ),
    )


def _mark_malformed(
    records: list[dict[str, object]],
    config: GeneratorConfig,
    source_name: str,
) -> None:
    selected = select_indices(
        len(records),
        config.quality.malformed_log_rate,
        random_for(
            config.seed,
            f"corruption.{source_name}.malformed",
        ),
    )

    for index in selected:
        records[index]["_ontology_sim_malformed"] = True


def _shift_hcp3_timestamp(
    value: str,
    seconds: float,
) -> str:
    # HCP3 intentionally uses an ECU-local timestamp without timezone.
    timestamp = datetime.strptime(  # noqa: DTZ007
        value,
        "%Y-%m-%d %H:%M:%S.%f",
    )

    timestamp += timedelta(seconds=seconds)

    return timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def _shift_hcp5_timestamp(
    value: str,
    seconds: float,
) -> str:
    # HCP5 intentionally uses a local structured timestamp without timezone.
    timestamp = datetime.strptime(  # noqa: DTZ007
        value,
        "%d.%m.%Y %H:%M:%S.%f",
    )

    timestamp += timedelta(seconds=seconds)

    return timestamp.strftime("%d.%m.%Y %H:%M:%S.%f")[:-3]


def _shift_conmod_timestamp(
    value: str,
    seconds: float,
) -> str:
    timestamp = datetime.fromisoformat(value)

    timestamp += timedelta(seconds=seconds)

    return timestamp.isoformat().replace("+00:00", "Z")
