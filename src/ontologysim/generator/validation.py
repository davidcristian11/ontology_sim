from pathlib import Path


def validate_written_files(
    paths: list[Path],
) -> None:
    if not paths:
        raise ValueError("No source files were written.")

    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Expected generated file does not exist: {path}")

        if path.stat().st_size == 0:
            raise ValueError(f"Generated file is empty: {path}")
