from copy import deepcopy
from random import Random


def select_indices(
    count: int,
    rate: float,
    rng: Random,
) -> set[int]:
    if count == 0 or rate <= 0:
        return set()

    selected_count = int(count * rate + 0.5)
    selected_count = min(count, selected_count)

    if selected_count == 0:
        return set()

    return set(
        rng.sample(
            range(count),
            k=selected_count,
        )
    )


def duplicate_records(
    records: list[dict[str, object]],
    rate: float,
    rng: Random,
) -> list[dict[str, object]]:
    output = deepcopy(records)

    selected = select_indices(
        len(records),
        rate,
        rng,
    )

    for index in sorted(selected):
        output.append(deepcopy(records[index]))

    return output


def remove_records(
    records: list[dict[str, object]],
    rate: float,
    rng: Random,
) -> list[dict[str, object]]:
    selected = select_indices(
        len(records),
        rate,
        rng,
    )

    return [record for index, record in enumerate(records) if index not in selected]


def set_field_to_none(
    records: list[dict[str, object]],
    field: str,
    rate: float,
    rng: Random,
) -> None:
    selected = select_indices(
        len(records),
        rate,
        rng,
    )

    for index in selected:
        records[index][field] = None
