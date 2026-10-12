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

# Stable test-case ID prefixes are already emitted by each scenario generator.
# Retain the original Bluetooth values and the existing CSV column contract.
TEST_PROCEDURES = {
    "BT": (
        "Vehicle sleeping; paired Bluetooth device available",
        "Wake vehicle; wait for connectivity initialization; observe Bluetooth reconnection",
    ),
    "NET": (
        "Online service active; cellular handover can be triggered",
        "Start online request; switch cellular route; verify service recovery",
    ),
    "CHG": (
        "Vehicle parked; compatible charger connected; battery ready to charge",
        "Start charging; monitor handshake and current; verify charging-state handling",
    ),
    "START": (
        "Vehicle off; infotainment ECU ready for a cold start",
        "Power on vehicle; observe service startup order and readiness timeouts",
    ),
    "NAV": (
        "Navigation active; GNSS position updates available for delay simulation",
        "Delay new GNSS fixes; monitor position age; verify stale-position handling",
    ),
    "AWAKE": (
        "Vehicle parked; no user activity; sleep eligibility conditions met",
        "Request vehicle sleep; monitor wake sources and ECU awake duration",
    ),
    "UPD": (
        "Software update available with version and interface dependencies",
        "Evaluate update compatibility; verify handling of incompatible interfaces",
    ),
    "POOR": (
        "Active connectivity session; degraded cellular conditions available",
        "Reduce signal quality; introduce packet loss; observe retry and recovery behavior",
    ),
}


def project_test_management(ground_truth: GroundTruth) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    for test_case in ground_truth.test_cases:
        # TC-<scenario-prefix>-<sequence>, e.g. TC-NAV-000001.
        prefix = test_case.test_case_id.split("-", 2)[1]
        if prefix not in TEST_PROCEDURES:
            raise ValueError(f"Unknown test-case scenario prefix: {test_case.test_case_id}")
        preconditions, test_steps = TEST_PROCEDURES[prefix]

        component_refs = [
            COMPONENT_ALIASES.get(component_id, component_names[component_id])
            for component_id in test_case.component_ids
        ]

        records.append(
            {
                "test_case_id": test_case.test_case_id,
                "title": test_case.title,
                "description": test_case.description,
                "test_type": test_case.test_type,
                "preconditions": preconditions,
                "test_steps": test_steps,
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
