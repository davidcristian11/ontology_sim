import csv
import json
from dataclasses import replace
from xml.etree import ElementTree as ET

from openpyxl import load_workbook

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.corruption import (
    apply_controlled_messiness,
)
from ontologysim.generator.pipeline import (
    generate_ground_truth,
)
from ontologysim.generator.projections import (
    project_all_sources,
)
from ontologysim.generator.writers import (
    write_all_sources,
)


def test_all_writers_create_readable_files(
    tmp_path,
) -> None:
    config = load_generator_config("config/generator.toml")

    profile = ProfileConfig(
        requirements=12,
        components=12,
        test_cases=12,
        test_executions=30,
        log_events=600,
        defects=3,
        trace_relationships=80,
    )

    config = replace(
        config,
        profile=profile,
    )

    ground_truth = generate_ground_truth(config)

    projected = project_all_sources(ground_truth)

    messy = apply_controlled_messiness(
        projected,
        config,
    )

    written = write_all_sources(
        messy,
        tmp_path,
    )

    assert len(written) == 9

    for path in written:
        assert path.exists()
        assert path.stat().st_size > 0

    ET.parse(tmp_path / "requirements" / "requirements.reqif")

    ET.parse(tmp_path / "architecture" / "architecture.arxml")

    with (tmp_path / "test_management" / "test_cases.csv").open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(csv.DictReader(file))
        assert rows

    with (tmp_path / "test_execution" / "test_executions.jsonl").open(
        encoding="utf-8",
    ) as file:
        first = json.loads(file.readline())
        assert "execution_id" in first

    with (tmp_path / "runtime" / "conmod" / "conmod_runtime.jsonl").open(
        encoding="utf-8",
    ) as file:
        first = json.loads(file.readline())
        assert "event" in first

    workbook = load_workbook(
        tmp_path / "defects" / "kpm_defects.xlsx",
        read_only=True,
    )

    assert "KPM" in workbook.sheetnames

    workbook.close()

    with (tmp_path / "traces" / "trace_export.tsv").open(
        encoding="utf-8",
        newline="",
    ) as file:
        rows = list(
            csv.DictReader(
                file,
                delimiter="\t",
            )
        )

        assert rows
