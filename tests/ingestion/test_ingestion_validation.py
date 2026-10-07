import pytest

from ontologysim.ingestion.validation import (
    validate_row_accounting,
    validate_row_preservation,
)


def test_row_accounting_passes() -> None:
    validate_row_accounting(
        expected_rows=100,
        bronze_rows=95,
        quarantine_rows=5,
    )


def test_row_accounting_fails() -> None:
    with pytest.raises(ValueError, match="Row accounting mismatch"):
        validate_row_accounting(
            expected_rows=100,
            bronze_rows=94,
            quarantine_rows=5,
        )


def test_row_preservation_passes() -> None:
    validate_row_preservation(
        source_rows=100,
        target_rows=100,
    )


def test_row_preservation_fails() -> None:
    with pytest.raises(ValueError, match="Row preservation mismatch"):
        validate_row_preservation(
            source_rows=100,
            target_rows=99,
        )