from pathlib import Path


def write_hcp5_logs(
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
                _write_malformed_record(
                    file,
                    record,
                )
                continue

            line = (
                f"{_value(record.get('timestamp'))} "
                f"[{_value(record.get('severity'))}] "
                f"ecu={_value(record.get('ecu'))} "
                f"component={_value(record.get('component'))} "
                f"event={_value(record.get('event_code'))} "
                f"session={_value(record.get('session_id'))} "
                f"execution={_value(record.get('execution_id'))} "
                f"sw={_value(record.get('software_version'))} "
                f'msg="{_value(record.get("message"))}"'
            )

            file.write(line)
            file.write("\n")


def _write_malformed_record(
    file,
    record: dict[str, object],
) -> None:
    file.write(
        f"{_value(record.get('timestamp'))} ecu=HCP5 CORRUPTED {_value(record.get('message'))[:25]}"
    )

    file.write("\n")


def _value(value: object) -> str:
    if value is None:
        return ""

    return str(value).replace("\n", " ")
