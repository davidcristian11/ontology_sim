from ontologysim.generator.models import ECU, GroundTruth


def project_architecture(
    ground_truth: GroundTruth,
) -> dict[str, list[dict[str, object]]]:
    ecus = [
        {
            "ecu_id": "ECU-HCP3",
            "ecu_name": ECU.HCP3.value,
            "role": "Infotainment and user-facing connectivity",
        },
        {
            "ecu_id": "ECU-HCP5",
            "ecu_name": ECU.HCP5.value,
            "role": "Vehicle-state coordination and energy-related functions",
        },
        {
            "ecu_id": "ECU-CONMOD",
            "ecu_name": ECU.CONMOD.value,
            "role": "External connectivity and telematics",
        },
    ]

    ecu_ids = {
        ECU.HCP3: "ECU-HCP3",
        ECU.HCP5: "ECU-HCP5",
        ECU.CONMOD: "ECU-CONMOD",
    }

    components: list[dict[str, object]] = []

    for component in ground_truth.components:
        components.append(
            {
                "component_id": component.component_id,
                "component_name": component.component_name,
                "component_type": component.component_type,
                "ecu_id": ecu_ids[component.ecu],
                "responsibility": component.responsibility,
                "version": component.version,
                "status": component.status,
                "owner_team": component.owner_team,
                "parent_component_id": component.parent_component_id,
                "provided_interfaces": [],
                "required_interfaces": [],
                "provided_services": [],
                "required_services": [],
            }
        )

    return {
        "ecus": ecus,
        "components": components,
    }
