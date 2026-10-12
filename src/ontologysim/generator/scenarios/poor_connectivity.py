"""Intermittent cellular connectivity under poor signal conditions."""

from ontologysim.generator.models import ECU, LogSeverity
from ontologysim.generator.scenarios.shared_scenario import EventStep as E
from ontologysim.generator.scenarios.shared_scenario import ScenarioSpec

SPEC = ScenarioSpec(
    scenario_id="poor_network_connectivity",
    prefix="POOR",
    requirements=(
        ("Cellular connectivity shall recover under weak signal", "SWC-CON-CELL-002"),
        ("Network diagnostics shall identify degraded signal quality", "SWC-CON-DIAG-003"),
        ("Online service shall handle intermittent network availability", "SWC-HCP3-CONN-002"),
        ("Backend requests shall support bounded retry", "SWC-CON-BACKEND-004"),
    ),
    start_events=(
        E(
            0,
            ECU.CONMOD,
            "SWC-CON-CELL-002",
            "SIGNAL_LEVEL_LOW",
            LogSeverity.WARN,
            "Cellular signal level degraded.",
        ),
        E(
            120,
            ECU.CONMOD,
            "SWC-CON-DIAG-003",
            "PACKET_LOSS_DETECTED",
            LogSeverity.WARN,
            "Intermittent packet loss detected.",
        ),
        E(
            260,
            ECU.HCP3,
            "SWC-HCP3-CONN-002",
            "ONLINE_REQUEST_RETRY",
            LogSeverity.INFO,
            "Online request retried.",
        ),
        E(
            400,
            ECU.CONMOD,
            "SWC-CON-BACKEND-004",
            "BACKEND_RETRY_SCHEDULED",
            LogSeverity.INFO,
            "Backend retry scheduled.",
        ),
    ),
    pass_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-CELL-002",
            "SIGNAL_RECOVERED",
            LogSeverity.INFO,
            "Cellular signal recovered.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-CONN-002",
            "ONLINE_REQUEST_COMPLETED",
            LogSeverity.INFO,
            "Online request completed after retry.",
        ),
    ),
    fail_events=(
        E(
            900,
            ECU.CONMOD,
            "SWC-CON-DIAG-003",
            "PACKET_LOSS_CONTINUES",
            LogSeverity.WARN,
            "Packet loss remains elevated.",
        ),
        E(
            1400,
            ECU.HCP3,
            "SWC-HCP3-CONN-002",
            "CONNECTIVITY_TIMEOUT",
            LogSeverity.ERROR,
            "Online request timed out under poor signal.",
        ),
    ),
    defect_title="Intermittent connectivity causes service failure",
    defect_component_id="SWC-CON-CELL-002",
    failure_reason="Weak cellular signal and packet loss caused repeated service timeouts.",
    filler_event_types=("SIGNAL_STRENGTH_SAMPLE", "PACKET_LOSS_SAMPLE"),
)
