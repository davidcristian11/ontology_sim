"""Vehicle remains awake after expected sleep deadline."""

from ontologysim.generator.models import ECU, LogSeverity
from ontologysim.generator.scenarios.shared_scenario import EventStep as E
from ontologysim.generator.scenarios.shared_scenario import ScenarioSpec

SPEC = ScenarioSpec(
    scenario_id="extended_vehicle_awake",
    prefix="AWAKE",
    requirements=(
        ("Vehicle shall enter sleep after the inactivity deadline", "SWC-HCP5-WAKE-002"),
        ("Energy management shall detect unexpected awake time", "SWC-HCP5-ENERGY-004"),
        ("Infotainment shall release background wake inhibitors", "SWC-HCP3-MEDIA-003"),
        ("Connectivity sessions shall release wake locks", "SRV-CON-NET-001"),
    ),
    start_events=(
        E(
            0,
            ECU.HCP5,
            "SWC-HCP5-WAKE-002",
            "SLEEP_REQUEST",
            LogSeverity.INFO,
            "Vehicle sleep requested.",
        ),
        E(
            120,
            ECU.HCP3,
            "SWC-HCP3-MEDIA-003",
            "MEDIA_SESSION_STOP",
            LogSeverity.INFO,
            "Media session stop requested.",
        ),
        E(
            260,
            ECU.CONMOD,
            "SRV-CON-NET-001",
            "BACKGROUND_SESSION_RELEASE",
            LogSeverity.INFO,
            "Background connectivity releasing.",
        ),
        E(
            400,
            ECU.HCP5,
            "SWC-HCP5-ENERGY-004",
            "SLEEP_INHIBITOR_CHECK",
            LogSeverity.INFO,
            "Wake inhibitors checked.",
        ),
    ),
    pass_events=(
        E(
            900,
            ECU.HCP5,
            "SWC-HCP5-WAKE-002",
            "SLEEP_CONDITIONS_READY",
            LogSeverity.INFO,
            "No wake inhibitors remain.",
        ),
        E(
            1400,
            ECU.HCP5,
            "SWC-HCP5-WAKE-002",
            "VEHICLE_ASLEEP",
            LogSeverity.INFO,
            "Vehicle entered sleep.",
        ),
    ),
    fail_events=(
        E(
            900,
            ECU.HCP3,
            "SWC-HCP3-MEDIA-003",
            "WAKE_LOCK_STILL_HELD",
            LogSeverity.WARN,
            "Media session still holds wake lock.",
        ),
        E(
            1400,
            ECU.HCP5,
            "SWC-HCP5-ENERGY-004",
            "SLEEP_TIMEOUT",
            LogSeverity.ERROR,
            "Vehicle remained awake beyond sleep deadline.",
        ),
    ),
    defect_title="Vehicle remains awake longer than expected",
    defect_component_id="SWC-HCP5-WAKE-002",
    failure_reason="A background service prevented timely vehicle sleep.",
    filler_event_types=("AWAKE_CURRENT_SAMPLE", "SLEEP_INHIBITOR_SAMPLE"),
)
