from ontologysim.generator.models import GroundTruth

COMPONENT_ALIASES = {
    "SWC-HCP3-BT-001": "BT reconnect module",
}


def project_defects(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    records: list[dict[str, object]] = []

    for defect in ground_truth.defects:
        affected_component = COMPONENT_ALIASES.get(
            defect.affected_component_id,
            component_names[defect.affected_component_id],
        )

        records.append(
            {
                "defect_id": defect.defect_id,
                "title": defect.title,
                "description": defect.description,
                "severity": defect.severity,
                "priority": defect.priority,
                "status": defect.status,
                "responsible_team": defect.responsible_team,
                "reporter": "Automated Test System",
                "created_at": defect.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": defect.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                "affected_ecu": defect.affected_ecu.value,
                "affected_component": affected_component,
                "affected_software_version": (defect.affected_software_version),
                "requirement_refs": ";".join(defect.requirement_ids),
                "test_case_refs": ";".join(defect.test_case_ids),
                "test_execution_refs": ";".join(defect.execution_ids),
                "resolution": None,
                "root_cause": defect.root_cause,
                "duplicate_of": None,
            }
        )

    return records
