from ontologysim.generator.models import GroundTruth


def project_requirements(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    component_names = {
        component.component_id: component.component_name for component in ground_truth.components
    }

    records: list[dict[str, object]] = []

    for requirement in ground_truth.requirements:
        target_component = None

        if requirement.target_component_id is not None:
            target_component = component_names[requirement.target_component_id]

        records.append(
            {
                "requirement_id": requirement.requirement_id,
                "title": requirement.title,
                "description": requirement.description,
                "requirement_type": requirement.requirement_type,
                "priority": requirement.priority,
                "status": requirement.status,
                "owner_team": requirement.owner_team,
                "version": requirement.version,
                "created_at": requirement.created_at.isoformat(),
                "updated_at": requirement.updated_at.isoformat(),
                "parent_requirement_id": (requirement.parent_requirement_id),
                "related_requirement_ids": list(requirement.related_requirement_ids),
                "target_ecu": (
                    requirement.target_ecu.value if requirement.target_ecu is not None else None
                ),
                "target_component": target_component,
                "verification_method": requirement.verification_method,
            }
        )

    return records
