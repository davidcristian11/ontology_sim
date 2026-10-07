from pathlib import Path

from ontologysim.generator.writers.architecture import (
    write_architecture,
)
from ontologysim.generator.writers.conmod_logs import (
    write_conmod_logs,
)
from ontologysim.generator.writers.defects import write_defects
from ontologysim.generator.writers.hcp3_logs import write_hcp3_logs
from ontologysim.generator.writers.hcp5_logs import write_hcp5_logs
from ontologysim.generator.writers.requirements import (
    write_requirements,
)
from ontologysim.generator.writers.test_execution import (
    write_test_executions,
)
from ontologysim.generator.writers.test_management import (
    write_test_management,
)
from ontologysim.generator.writers.traces import write_traces


def get_output_paths(
    output_dir: Path,
) -> dict[str, Path]:
    return {
        "requirements": output_dir / "requirements" / "requirements.reqif",
        "architecture": output_dir / "architecture" / "architecture.arxml",
        "test_management": output_dir / "test_management" / "test_cases.csv",
        "test_execution": output_dir / "test_execution" / "test_executions.jsonl",
        "hcp3_logs": output_dir / "runtime" / "hcp3" / "hcp3_runtime.dlt",
        "hcp5_logs": output_dir / "runtime" / "hcp5" / "hcp5_runtime.log",
        "conmod_logs": output_dir / "runtime" / "conmod" / "conmod_runtime.jsonl",
        "defects": output_dir / "defects" / "kpm_defects.xlsx",
        "traces": output_dir / "traces" / "trace_export.tsv",
    }


def write_static_sources(
    sources: dict[str, object],
    output_dir: Path,
) -> list[Path]:
    paths = get_output_paths(output_dir)

    write_requirements(
        sources["requirements"],
        paths["requirements"],
    )

    write_architecture(
        sources["architecture"],
        paths["architecture"],
    )

    write_test_management(
        sources["test_management"],
        paths["test_management"],
    )

    write_test_executions(
        sources["test_execution"],
        paths["test_execution"],
    )

    write_defects(
        sources["defects"],
        paths["defects"],
    )

    write_traces(
        sources["traces"],
        paths["traces"],
    )

    return [
        paths["requirements"],
        paths["architecture"],
        paths["test_management"],
        paths["test_execution"],
        paths["defects"],
        paths["traces"],
    ]


def write_runtime_sources(
    sources: dict[str, object],
    output_dir: Path,
    *,
    append: bool,
) -> list[Path]:
    paths = get_output_paths(output_dir)

    write_hcp3_logs(
        sources["hcp3_logs"],
        paths["hcp3_logs"],
        append=append,
    )

    write_hcp5_logs(
        sources["hcp5_logs"],
        paths["hcp5_logs"],
        append=append,
    )

    write_conmod_logs(
        sources["conmod_logs"],
        paths["conmod_logs"],
        append=append,
    )

    return [
        paths["hcp3_logs"],
        paths["hcp5_logs"],
        paths["conmod_logs"],
    ]


def write_all_sources(
    sources: dict[str, object],
    output_dir: Path,
) -> list[Path]:
    static = write_static_sources(
        sources,
        output_dir,
    )

    runtime = write_runtime_sources(
        sources,
        output_dir,
        append=False,
    )

    return static + runtime
