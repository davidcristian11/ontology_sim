from ontologysim.generator.models import ECU, GroundTruth, LogEvent

COMPONENT_ALIASES = {
    "SWC-HCP3-BT-001": "BT_CONN_MGR",
    "SWC-HCP3-CONN-002": "CONN_STATUS_SVC",
    "SWC-HCP3-MEDIA-003": "MEDIA_SESS_MGR",
    "SWC-HCP3-PROFILE-004": "USR_PROFILE_MGR",
}

# Native HCP3 logging contexts, based on the emitting component.
COMPONENT_CONTEXTS = {
    "SWC-HCP3-BT-001": "BT",
    "SWC-HCP3-CONN-002": "CONNECTIVITY",
    "SWC-HCP3-MEDIA-003": "MEDIA",
    "SWC-HCP3-PROFILE-004": "PROFILE",
    "SWC-HCP3-BOOT-005": "STARTUP",
    "SWC-HCP3-NAV-006": "NAVIGATION",
    "SWC-HCP3-UPD-007": "UPDATE",
}


def _context_id(event: LogEvent) -> str:
    # Preserve the original V1 Bluetooth context.
    # V1 and V2's Bluetooth slice use numeric LOG- IDs.
    if event.event_id.startswith("LOG-") and event.event_id[4:].isdigit():
        return "BT"

    return COMPONENT_CONTEXTS.get(event.component_id, "SYSTEM")


def project_hcp3_logs(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    for event in ground_truth.log_events:
        if event.ecu != ECU.HCP3:
            continue

        component_name = COMPONENT_ALIASES.get(
            event.component_id,
            component_names[event.component_id],
        )

        event_number = int(event.event_id.rsplit("-", 1)[1])

        records.append(
            {
                "_ontology_sim_event_id": event.event_id,
                "timestamp": event.timestamp.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                "ecu_id": "HCP3",
                "application_id": "INFOTAINMENT",
                "context_id": _context_id(event),
                "component_name": component_name,
                "severity": event.severity.value,
                "event_type": event.event_type,
                "message": event.message,
                "session_id": event.session_id,
                "execution_id": event.execution_id,
                "software_version": event.software_version,
                "thread_id": f"thr-{event_number % 32:02d}",
            }
        )

    return records
