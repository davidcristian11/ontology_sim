"""Infotainment starts before the required vehicle state is available."""

from ontologysim.generator.models import ECU, LogSeverity
from ontologysim.generator.scenarios.shared_scenario import EventStep as E
from ontologysim.generator.scenarios.shared_scenario import ScenarioSpec

SPEC = ScenarioSpec(
    scenario_id="infotainment_startup_sequence",
    prefix="START",
    requirements=(
        ("Infotainment startup shall wait for vehicle-state readiness", "SWC-HCP3-BOOT-005"),
        ("Wake coordination shall publish readiness before dependent startup", "SWC-HCP5-WAKE-002"),
        ("Vehicle state shall be distributed to HCP3", "SWC-HCP5-STATE-003"),
    ),
    start_events=(
        E(
            0,
            ECU.HCP5,
            "SWC-HCP5-WAKE-002",
            "VEHICLE_WAKE",
            LogSeverity.INFO,
            "Vehicle wake triggered.",
        ),
        E(
            120,
            ECU.HCP3,
            "SWC-HCP3-BOOT-005",
            "STARTUP_REQUESTED",
            LogSeverity.INFO,
            "Infotainment startup requested.",
        ),
        E(
            260,
            ECU.HCP5,
            "SWC-HCP5-STATE-003",
            "STATE_DISTRIBUTION_PENDING",
            LogSeverity.INFO,
            "Vehicle state pending.",
        ),
        E(
            400,
            ECU.HCP3,
            "SWC-HCP3-BOOT-005",
            "STARTUP_STATE_CHECK",
            LogSeverity.INFO,
            "Startup dependency checked.",
        ),
    ),
    pass_events=(
        E(
            900,
            ECU.HCP5,
            "SWC-HCP5-STATE-003",
            "VEHICLE_STATE_READY",
            LogSeverity.INFO,
            "Vehicle state delivered.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-BOOT-005",
            "STARTUP_COMPLETED",
            LogSeverity.INFO,
            "Infotainment startup completed.",
        ),
    ),
    fail_events=(
        E(
            900,
            ECU.HCP3,
            "SWC-HCP3-BOOT-005",
            "STARTUP_BEFORE_STATE",
            LogSeverity.WARN,
            "Startup continued before state was ready.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-BOOT-005",
            "STARTUP_DEPENDENCY_ERROR",
            LogSeverity.ERROR,
            "Infotainment startup failed on missing vehicle state.",
        ),
    ),
    defect_title="Infotainment startup ordering failure",
    defect_component_id="SWC-HCP3-BOOT-005",
    failure_reason="Infotainment began before the required vehicle state arrived.",
    filler_event_types=("STARTUP_PHASE_SAMPLE", "VEHICLE_STATE_HEARTBEAT"),
)
