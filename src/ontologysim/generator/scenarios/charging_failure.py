"""Charging-session failure: HCP5 and ConMod."""

from ontologysim.generator.models import ECU, LogSeverity
from ontologysim.generator.scenarios.shared_scenario import EventStep as E
from ontologysim.generator.scenarios.shared_scenario import ScenarioSpec

SPEC = ScenarioSpec(
    scenario_id="charging_session_failure",
    prefix="CHG",
    requirements=(
        ("Charging session shall enter active state after authorization", "SWC-HCP5-CHG-005"),
        ("Energy state shall permit charging when conditions are valid", "SWC-HCP5-ENERGY-004"),
        ("Backend authorization shall be available for charging", "SWC-CON-BACKEND-004"),
    ),
    start_events=(
        E(
            0,
            ECU.HCP5,
            "SWC-HCP5-CHG-005",
            "CHARGE_PLUG_DETECTED",
            LogSeverity.INFO,
            "Charging connector detected.",
        ),
        E(
            120,
            ECU.HCP5,
            "SWC-HCP5-ENERGY-004",
            "ENERGY_READY",
            LogSeverity.INFO,
            "Energy management allows charging.",
        ),
        E(
            260,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "AUTH_REQUEST",
            LogSeverity.INFO,
            "Charging authorization requested.",
        ),
        E(
            400,
            ECU.HCP5,
            "SWC-HCP5-CHG-005",
            "CHARGE_START_REQUEST",
            LogSeverity.INFO,
            "Charging start requested.",
        ),
    ),
    pass_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "AUTH_APPROVED",
            LogSeverity.INFO,
            "Charging authorized.",
        ),
        E(
            1400,
            ECU.HCP5,
            "SWC-HCP5-CHG-005",
            "CHARGE_ACTIVE",
            LogSeverity.INFO,
            "Charging session active.",
        ),
    ),
    fail_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "AUTH_DELAYED",
            LogSeverity.WARN,
            "Charging authorization not received.",
        ),
        E(
            1400,
            ECU.HCP5,
            "SWC-HCP5-CHG-005",
            "CHARGE_START_FAILED",
            LogSeverity.ERROR,
            "Charging failed to start.",
        ),
    ),
    defect_title="Charging session fails to start",
    defect_component_id="SWC-HCP5-CHG-005",
    failure_reason="Charging session did not transition to active after authorization delay.",
    filler_event_types=("CHARGE_STATE_SAMPLE", "ENERGY_STATUS_SAMPLE"),
)
