from pathlib import Path

FIELDS = (
    "timestamp",
    "ecu_id",
    "application_id",
    "context_id",
    "component_name",
    "severity",
    "event_type",
    "message",
    "session_id",
    "execution_id",
    "software_version",
    "thread_id",
)


def write_hcp3_logs(
    records: list[dict[str, object]],
    path: Path,
    *,
    append: bool = False,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    mode = "a" if append else "w"

    with path.open(
        mode,
        encoding="utf-8",
    ) as file:
        for record in records:
            if record.get("_ontology_sim_malformed"):
                _write_malformed_record(file, record)
                continue

            values = [_string_value(record.get(field)) for field in FIELDS]

            file.write("|".join(values))
            file.write("\n")


def _write_malformed_record(
    file,
    record: dict[str, object],
) -> None:
    timestamp = _string_value(record.get("timestamp"))

    component = _string_value(record.get("component_name"))

    message = _string_value(record.get("message"))

    file.write(f"{timestamp}|HCP3|{component}|{message[:30]}")

    file.write("\n")


def _string_value(value: object) -> str:
    if value is None:
        return ""

    return str(value).replace("\n", " ")
