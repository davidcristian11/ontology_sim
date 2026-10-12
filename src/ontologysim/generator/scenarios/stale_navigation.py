"""Navigation position freshness: HCP3 and ConMod GNSS."""

from ontologysim.generator.models import ECU, LogSeverity
from ontologysim.generator.scenarios.shared_scenario import EventStep as E
from ontologysim.generator.scenarios.shared_scenario import ScenarioSpec

SPEC = ScenarioSpec(
    scenario_id="stale_navigation_position",
    prefix="NAV",
    requirements=(
        ("GNSS shall publish fresh timestamped location fixes", "SRV-CON-GNSS-005"),
        ("Navigation shall reject stale position updates", "SWC-HCP3-NAV-006"),
        ("GNSS diagnostics shall report lost fix updates", "SWC-CON-DIAG-003"),
    ),
    start_events=(
        E(
            0,
            ECU.CONMOD,
            "SRV-CON-GNSS-005",
            "GNSS_FIX_VALID",
            LogSeverity.INFO,
            "Valid GNSS fix available.",
        ),
        E(
            120,
            ECU.HCP3,
            "SWC-HCP3-NAV-006",
            "NAV_POSITION_CONSUMED",
            LogSeverity.INFO,
            "Navigation consumed current position.",
        ),
        E(
            260,
            ECU.CONMOD,
            "SRV-CON-GNSS-005",
            "GNSS_UPDATE_EXPECTED",
            LogSeverity.INFO,
            "Next GNSS fix expected.",
        ),
        E(
            400,
            ECU.HCP3,
            "SWC-HCP3-NAV-006",
            "POSITION_AGE_CHECK",
            LogSeverity.INFO,
            "Navigation checked position freshness.",
        ),
    ),
    pass_events=(
        E(
            900,
            ECU.CONMOD,
            "SRV-CON-GNSS-005",
            "GNSS_FIX_REFRESHED",
            LogSeverity.INFO,
            "Fresh position fix delivered.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-NAV-006",
            "NAV_POSITION_FRESH",
            LogSeverity.INFO,
            "Navigation position remains fresh.",
        ),
    ),
    fail_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-DIAG-003",
            "GNSS_UPDATE_MISSING",
            LogSeverity.WARN,
            "No new GNSS fix arrived.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-NAV-006",
            "NAV_POSITION_STALE",
            LogSeverity.ERROR,
            "Navigation position exceeded freshness limit.",
        ),
    ),
    defect_title="Navigation position becomes stale",
    defect_component_id="SWC-HCP3-NAV-006",
    failure_reason="Navigation used a position older than the permitted freshness threshold.",
    filler_event_types=("GNSS_FIX_AGE_SAMPLE", "POSITION_HEALTH_SAMPLE"),
)
