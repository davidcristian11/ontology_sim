from ontologysim.generator.models import ECU, GroundTruth


def project_hcp5_logs(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    for event in ground_truth.log_events:
        if event.ecu != ECU.HCP5:
            continue

        records.append(
            {
                "_ontology_sim_event_id": event.event_id,
                "timestamp": event.timestamp.strftime("%d.%m.%Y %H:%M:%S.%f")[:-3],
                "severity": event.severity.value,
                "ecu": "HCP5",
                "component": component_names[event.component_id],
                "event_code": event.event_type,
                "session_id": event.session_id,
                "execution_id": event.execution_id,
                "software_version": event.software_version,
                "message": event.message,
            }
        )

    return records
