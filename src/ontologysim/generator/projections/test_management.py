from ontologysim.generator.models import GroundTruth

COMPONENT_ALIASES = {
    "SWC-HCP3-BT-001": "BluetoothManager",
    "SWC-HCP3-CONN-002": "ConnectivityStatus",
    "SWC-HCP3-MEDIA-003": "MediaManager",
    "SWC-HCP3-PROFILE-004": "ProfileManager",
    "SWC-HCP5-PWR-001": "PowerStateManager",
    "SWC-HCP5-WAKE-002": "WakeCoordinator",
    "SWC-HCP5-STATE-003": "VehicleStateService",
    "SWC-HCP5-ENERGY-004": "EnergyService",
    "SRV-CON-NET-001": "ConnectivityService",
    "SWC-CON-CELL-002": "CellularManager",
    "SWC-CON-DIAG-003": "NetworkDiagnostics",
    "SWC-CON-BACKEND-004": "BackendService",
}


def project_test_management(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    for test_case in ground_truth.test_cases:
        component_refs = [
            COMPONENT_ALIASES.get(
                component_id,
                component_names[component_id],
            )
            for component_id in test_case.component_ids
        ]

        records.append(
            {
                "test_case_id": test_case.test_case_id,
                "title": test_case.title,
                "description": test_case.description,
                "test_type": test_case.test_type,
                "preconditions": ("Vehicle sleeping; paired Bluetooth device available"),
                "test_steps": (
                    "Wake vehicle; wait for connectivity initialization; "
                    "observe Bluetooth reconnection"
                ),
                "expected_result": test_case.expected_result,
                "priority": test_case.priority,
                "status": test_case.status,
                "owner_team": test_case.owner_team,
                "version": test_case.version,
                "requirement_refs": ";".join(test_case.requirement_ids),
                "component_refs": ";".join(component_refs),
                "target_ecu": test_case.target_ecu.value,
                "created_at": test_case.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": test_case.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

    return records
