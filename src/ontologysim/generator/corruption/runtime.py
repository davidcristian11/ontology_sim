import hashlib
from copy import deepcopy
from datetime import datetime, timedelta

from ontologysim.generator.config import GeneratorConfig


def apply_runtime_messiness(
    projected: dict[str, object],
    config: GeneratorConfig,
) -> dict[str, object]:
    sources = deepcopy(projected)

    sources["hcp3_logs"] = _corrupt_hcp3(
        _records(sources, "hcp3_logs"),
        config,
    )

    sources["hcp5_logs"] = _corrupt_hcp5(
        _records(sources, "hcp5_logs"),
        config,
    )

    sources["conmod_logs"] = _corrupt_conmod(
        _records(sources, "conmod_logs"),
        config,
    )

    return sources


def _records(
    sources: dict[str, object],
    name: str,
) -> list[dict[str, object]]:
    value = sources[name]

    if not isinstance(value, list):
        raise TypeError(f"{name} must contain a list")

    return value


def _selected(
    seed: int,
    namespace: str,
    event_id: str,
    rate: float,
) -> bool:
    if rate <= 0:
        return False

    payload = (f"{seed}:{namespace}:{event_id}").encode()

    digest = hashlib.sha256(payload).digest()

    value = (
        int.from_bytes(
            digest[:8],
            byteorder="big",
            signed=False,
        )
        / 2**64
    )

    return value < rate


def _event_id(
    record: dict[str, object],
) -> str:
    value = record.get("_ontology_sim_event_id")

    if not isinstance(value, str):
        raise TypeError("Runtime record is missing _ontology_sim_event_id")

    return value


def _corrupt_hcp3(
    records: list[dict[str, object]],
    config: GeneratorConfig,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []

    for source_record in records:
        record = deepcopy(source_record)
        event_id = _event_id(record)

        timestamp = record.get("timestamp")

        if isinstance(timestamp, str):
            record["timestamp"] = _shift_hcp3_timestamp(
                timestamp,
                config.clock_drift.hcp3,
            )

        if _selected(
            config.seed,
            "hcp3.missing_execution",
            event_id,
            config.quality.missing_link_rate,
        ):
            record["execution_id"] = None

        if _selected(
            config.seed,
            "hcp3.missing_thread",
            event_id,
            config.quality.missing_field_rate,
        ):
            record["thread_id"] = None

        if _selected(
            config.seed,
            "hcp3.malformed",
            event_id,
            config.quality.malformed_log_rate,
        ):
            record["_ontology_sim_malformed"] = True

        output.append(record)

        if _selected(
            config.seed,
            "hcp3.duplicate",
            event_id,
            config.quality.duplicate_record_rate,
        ):
            output.append(deepcopy(record))

    return output


def _corrupt_hcp5(
    records: list[dict[str, object]],
    config: GeneratorConfig,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []

    for source_record in records:
        record = deepcopy(source_record)
        event_id = _event_id(record)

        timestamp = record.get("timestamp")

        if isinstance(timestamp, str):
            record["timestamp"] = _shift_hcp5_timestamp(
                timestamp,
                config.clock_drift.hcp5,
            )

        if _selected(
            config.seed,
            "hcp5.missing_session",
            event_id,
            config.quality.missing_link_rate,
        ):
            record["session_id"] = None

        if _selected(
            config.seed,
            "hcp5.missing_execution",
            event_id,
            config.quality.missing_field_rate,
        ):
            record["execution_id"] = None

        if _selected(
            config.seed,
            "hcp5.malformed",
            event_id,
            config.quality.malformed_log_rate,
        ):
            record["_ontology_sim_malformed"] = True

        output.append(record)

        if _selected(
            config.seed,
            "hcp5.duplicate",
            event_id,
            config.quality.duplicate_record_rate,
        ):
            output.append(deepcopy(record))

    return output


def _corrupt_conmod(
    records: list[dict[str, object]],
    config: GeneratorConfig,
) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []

    for source_record in records:
        record = deepcopy(source_record)
        event_id = _event_id(record)

        timestamp = record.get("timestamp")

        if isinstance(timestamp, str):
            record["timestamp"] = _shift_conmod_timestamp(
                timestamp,
                config.clock_drift.conmod,
            )

        if _selected(
            config.seed,
            "conmod.missing_execution",
            event_id,
            config.quality.missing_link_rate,
        ):
            record["execution_ref"] = None

        if _selected(
            config.seed,
            "conmod.missing_network",
            event_id,
            config.quality.missing_field_rate,
        ):
            record["network_type"] = None

        output.append(record)

        if _selected(
            config.seed,
            "conmod.duplicate",
            event_id,
            config.quality.duplicate_record_rate,
        ):
            output.append(deepcopy(record))

    return output


def _shift_hcp3_timestamp(
    value: str,
    seconds: float,
) -> str:
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

    return timestamp.isoformat().replace(
        "+00:00",
        "Z",
    )
