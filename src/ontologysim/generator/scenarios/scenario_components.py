"""Additional V2 components; existing V1 IDs remain unchanged."""

from collections.abc import Sequence

from ontologysim.generator.models import ECU, Component

EXTRA_COMPONENTS = (
    (
        "SWC-HCP5-CHG-005",
        "ChargingStateManager",
        ECU.HCP5,
        "Coordinates charging-session states.",
        "Charging",
    ),
    (
        "SWC-HCP3-BOOT-005",
        "InfotainmentStartupCoordinator",
        ECU.HCP3,
        "Sequences infotainment startup.",
        "Infotainment",
    ),
    (
        "SWC-HCP3-NAV-006",
        "NavigationPositionService",
        ECU.HCP3,
        "Consumes and validates navigation positions.",
        "Navigation",
    ),
    (
        "SRV-CON-GNSS-005",
        "GNSSService",
        ECU.CONMOD,
        "Publishes GNSS fixes with age and validity.",
        "Navigation",
    ),
    (
        "SWC-HCP3-UPD-007",
        "SoftwareCompatibilityChecker",
        ECU.HCP3,
        "Checks software interface compatibility.",
        "Platform",
    ),
)


def extend_component_catalog(
    components: Sequence[Component],
) -> list[Component]:
    """Append V2 components without duplicating V1 components."""
    result = list(components)
    existing = {component.component_id for component in result}

    for identifier, name, ecu, responsibility, team in EXTRA_COMPONENTS:
        if identifier not in existing:
            result.append(
                Component(
                    component_id=identifier,
                    component_name=name,
                    component_type=(
                        "SoftwareComponent" if identifier.startswith("SWC") else "Service"
                    ),
                    ecu=ecu,
                    responsibility=responsibility,
                    version="3.4.0",
                    status="Active",
                    owner_team=team,
                )
            )
            existing.add(identifier)

    return result
