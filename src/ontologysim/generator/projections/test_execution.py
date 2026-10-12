from ontologysim.generator.models import GroundTruth

# Executor names follow the existing test-suite identifiers.
# The Bluetooth V1 value remains unchanged.
EXECUTORS_BY_TEST_PREFIX = {
    "BT": "automated_bt_regression",
    "NET": "automated_connectivity_regression",
    "CHG": "automated_charging_regression",
    "START": "automated_startup_regression",
    "NAV": "automated_navigation_regression",
    "AWAKE": "automated_power_management_regression",
    "UPD": "automated_software_compatibility",
    "POOR": "automated_connectivity_stress",
}


def _executor_for_test_case(test_case_id: str) -> str:
    parts = test_case_id.split("-", 2)

    if len(parts) == 3 and parts[0] == "TC":
        return EXECUTORS_BY_TEST_PREFIX.get(
            parts[1],
            "automated_vehicle_regression",
        )

    return "automated_vehicle_regression"


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
                "start_timestamp": execution.start_timestamp.isoformat(),
                "end_timestamp": (
                    execution.end_timestamp.isoformat()
                    if execution.end_timestamp is not None
                    else None
                ),
                "duration_ms": duration_ms,
                "result": execution.result.value,
                "execution_environment": "VehicleBench",
                "vehicle_id": execution.vehicle_id,
                "software_version_hcp3": execution.software_version_hcp3,
                "software_version_hcp5": execution.software_version_hcp5,
                "software_version_conmod": execution.software_version_conmod,
                "hardware_configuration": "HW-OntologySim-V1",
                "executor": _executor_for_test_case(execution.test_case_id),
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
