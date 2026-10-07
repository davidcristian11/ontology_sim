def validate_row_accounting(
    expected_rows: int,
    bronze_rows: int,
    quarantine_rows: int = 0,
) -> None:
    accounted_rows = bronze_rows + quarantine_rows

    if accounted_rows != expected_rows:
        raise ValueError(
            f"Row accounting mismatch: expected {expected_rows}, "
            f"got {accounted_rows}"
        )


def validate_row_preservation(
    source_rows: int,
    target_rows: int,
) -> None:
    if source_rows != target_rows:
        raise ValueError(
            f"Row preservation mismatch: "
            f"source={source_rows}, target={target_rows}"
        )