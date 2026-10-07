from ontologysim.generator.models import GroundTruth
from ontologysim.generator.projections.architecture import (
    project_architecture,
)
from ontologysim.generator.projections.conmod_logs import (
    project_conmod_logs,
)
from ontologysim.generator.projections.defects import project_defects
from ontologysim.generator.projections.hcp3_logs import project_hcp3_logs
from ontologysim.generator.projections.hcp5_logs import project_hcp5_logs
from ontologysim.generator.projections.requirements import (
    project_requirements,
)
from ontologysim.generator.projections.test_execution import (
    project_test_executions,
)
from ontologysim.generator.projections.test_management import (
    project_test_management,
)
from ontologysim.generator.projections.traces import project_traces


def project_all_sources(
    ground_truth: GroundTruth,
) -> dict[str, object]:
    return {
        "requirements": project_requirements(ground_truth),
        "architecture": project_architecture(ground_truth),
        "test_management": project_test_management(ground_truth),
        "test_execution": project_test_executions(ground_truth),
        "hcp3_logs": project_hcp3_logs(ground_truth),
        "hcp5_logs": project_hcp5_logs(ground_truth),
        "conmod_logs": project_conmod_logs(ground_truth),
        "defects": project_defects(ground_truth),
        "traces": project_traces(ground_truth),
    }
