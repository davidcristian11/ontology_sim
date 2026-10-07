from ontologysim.generator.models import ECU, GroundTruth


def _connectivity_values(
    event_type: str,
) -> tuple[str, int, str]:
    if event_type == "CONNECTIVITY_READY":
        return "CONNECTED", -64, "CONNECTED"

    return "CONNECTED", -70, "CONNECTED"


def project_conmod_logs(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    for event in ground_truth.log_events:
        if event.ecu != ECU.CONMOD:
            continue

        connection_state, signal_strength, backend_state = _connectivity_values(event.event_type)

        timestamp = event.timestamp.isoformat().replace(
            "+00:00",
            "Z",
        )

        records.append(
            {
                "_ontology_sim_event_id": event.event_id,
                "timestamp": timestamp,
                "ecu": "ConMod",
                "service": component_names[event.component_id],
                "event": event.event_type,
                "severity": event.severity.value,
                "network_type": "CELLULAR",
                "connection_state": connection_state,
                "signal_strength": signal_strength,
                "backend_state": backend_state,
                "session_id": event.session_id,
                "execution_ref": event.execution_id,
                "software_build": event.software_version,
                "message": event.message,
            }
        )

    return records
