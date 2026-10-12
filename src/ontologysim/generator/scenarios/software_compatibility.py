"""Software update creates incompatible cross-ECU interfaces."""

from ontologysim.generator.models import ECU, LogSeverity
from ontologysim.generator.scenarios.shared_scenario import EventStep as E
from ontologysim.generator.scenarios.shared_scenario import ScenarioSpec

SPEC = ScenarioSpec(
    scenario_id="software_update_compatibility",
    prefix="UPD",
    requirements=(
        ("HCP3 shall validate software interface compatibility", "SWC-HCP3-UPD-007"),
        ("Vehicle state APIs shall remain compatible after an update", "SWC-HCP5-STATE-003"),
        ("Backend integration shall preserve supported protocol versions", "SWC-CON-BACKEND-004"),
    ),
    start_events=(
        E(
            0,
            ECU.HCP3,
            "SWC-HCP3-UPD-007",
            "UPDATE_ACTIVATED",
            LogSeverity.INFO,
            "New software version activated.",
        ),
        E(
            120,
            ECU.HCP5,
            "SWC-HCP5-STATE-003",
            "STATE_API_ADVERTISED",
            LogSeverity.INFO,
            "Vehicle-state API version advertised.",
        ),
        E(
            260,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "BACKEND_PROTOCOL_NEGOTIATION",
            LogSeverity.INFO,
            "Backend protocol negotiation started.",
        ),
        E(
            400,
            ECU.HCP3,
            "SWC-HCP3-UPD-007",
            "INTERFACE_VERSION_CHECK",
            LogSeverity.INFO,
            "Interface versions compared.",
        ),
    ),
    pass_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "PROTOCOL_COMPATIBLE",
            LogSeverity.INFO,
            "Protocol versions compatible.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-UPD-007",
            "COMPATIBILITY_VERIFIED",
            LogSeverity.INFO,
            "Cross-ECU compatibility verified.",
        ),
    ),
    fail_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "PROTOCOL_VERSION_MISMATCH",
            LogSeverity.WARN,
            "Incompatible backend protocol version.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-UPD-007",
            "INTERFACE_INCOMPATIBLE",
            LogSeverity.ERROR,
            "Cross-ECU interface compatibility check failed.",
        ),
    ),
    defect_title="Software update breaks interface compatibility",
    defect_component_id="SWC-HCP3-UPD-007",
    failure_reason="Software release requires an unsupported cross-ECU interface version.",
    filler_event_types=("INTERFACE_VERSION_SAMPLE", "COMPATIBILITY_STATUS_SAMPLE"),
    failure_hcp3_version="HCP3_3.5.0-B201",
)
