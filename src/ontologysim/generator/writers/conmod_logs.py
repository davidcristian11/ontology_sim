import json
from pathlib import Path


def write_conmod_logs(
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
            serializable = {
                key: value for key, value in record.items() if not key.startswith("_ontology_sim_")
            }

            file.write(
                json.dumps(
                    serializable,
                    ensure_ascii=False,
                )
            )

            file.write("\n")
