from ontologysim.generator.models import GroundTruth


def project_test_executions(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for execution in ground_truth.test_executions:
        duration_ms = None

        if execution.end_timestamp is not None:
            duration_ms = int(
                (execution.end_timestamp - execution.start_timestamp).total_seconds() * 1000
            )

        records.append(
            {
                "execution_id": execution.execution_id,
                "test_case_id": execution.test_case_id,
                "campaign_id": execution.campaign_id,
                "session_id": execution.session_id,
                "start_timestamp": (execution.start_timestamp.isoformat()),
                "end_timestamp": (
                    execution.end_timestamp.isoformat()
                    if execution.end_timestamp is not None
                    else None
                ),
                "duration_ms": duration_ms,
                "result": execution.result.value,
                "execution_environment": "VehicleBench",
                "vehicle_id": execution.vehicle_id,
                "software_version_hcp3": (execution.software_version_hcp3),
                "software_version_hcp5": (execution.software_version_hcp5),
                "software_version_conmod": (execution.software_version_conmod),
                "hardware_configuration": "HW-OntologySim-V1",
                "executor": "automated_bt_regression",
                "failure_reason": execution.failure_reason,
                "log_refs": [
                    f"hcp3:{execution.session_id}",
                    f"hcp5:{execution.session_id}",
                    f"conmod:{execution.session_id}",
                ],
                "measurement_refs": [],
            }
        )

    return records
