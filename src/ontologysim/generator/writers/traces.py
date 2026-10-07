import csv
from pathlib import Path


def write_traces(
    records: list[dict[str, object]],
    path: Path,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.touch()
        return

    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(records[0]),
            delimiter="\t",
        )

        writer.writeheader()
        writer.writerows(records)
