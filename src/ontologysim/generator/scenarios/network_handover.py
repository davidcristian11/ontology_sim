"""Network handover scenario. Not connected to the V1 pipeline yet."""

from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from ontologysim.generator.models import (
    ECU,
    Component,
    Defect,
    GroundTruth,
    Incident,
    LogEvent,
    LogSeverity,
    Requirement,
    TestCase,
    TestExecution,
    TestResult,
    TraceRelationship,
)
from ontologysim.generator.randoms import random_for

SCENARIO_ID = "online_service_network_handover"
BASE_TIME = datetime(2026, 10, 1, 8, tzinfo=UTC)

# Existing V1 component IDs.
HANDOVER_COMPONENT_IDS = (
    "SRV-CON-NET-001",
    "SWC-CON-CELL-002",
    "SWC-CON-BACKEND-004",
    "SWC-CON-DIAG-003",
    "SWC-HCP3-CONN-002",
)

_REQUIREMENT_TEMPLATES = (
    (
        "Cellular handover shall preserve network-session continuity",
        "SWC-CON-CELL-002",
    ),
    (
        "Connectivity state shall reflect a network handover",
        "SRV-CON-NET-001",
    ),
    (
        "Backend communication shall recover after route restoration",
        "SWC-CON-BACKEND-004",
    ),
    (
        "Handover diagnostics shall identify lost connectivity",
        "SWC-CON-DIAG-003",
    ),
    (
        "Online service status shall recover following network handover",
        "SWC-HCP3-CONN-002",
    ),
)


@dataclass(frozen=True, slots=True)
class NetworkHandoverPlan:
    """Quotas for one network-handover scenario slice."""

    seed: int
    requirements: int
    test_cases: int
    test_executions: int
    log_events: int
    defects: int
    trace_relationships: int
    failure_rate: float = 0.16
    defect_probability_given_failure: float = 0.20


def generate_network_handover_ground_truth(
    plan: NetworkHandoverPlan,
    components: Sequence[Component],
    *,
    materialize_logs: bool = True,
) -> GroundTruth:
    """Generate clean, connected network-handover engineering data."""

    _validate(plan, components)

    catalog = {component.component_id: component for component in components}

    rng = random_for(
        plan.seed,
        "handover:engineering",
    )

    requirements: list[Requirement] = []

    for index in range(1, plan.requirements + 1):
        title, component_id = _REQUIREMENT_TEMPLATES[(index - 1) % len(_REQUIREMENT_TEMPLATES)]

        component = catalog[component_id]

        prefix = "HCP3" if component.ecu == ECU.HCP3 else "CON"

        created = BASE_TIME - timedelta(days=rng.randint(30, 365))

        requirements.append(
            Requirement(
                requirement_id=f"REQ-{prefix}-NH-{index:06d}",
                title=f"{title} #{index}",
                description=(f"{title} during cellular network handover."),
                requirement_type="Functional",
                priority="High" if index % 3 == 0 else "Medium",
                status="Approved",
                owner_team=component.owner_team,
                version="1.0",
                created_at=created,
                updated_at=created + timedelta(days=7),
                target_ecu=component.ecu,
                target_component_id=component_id,
                verification_method="Test",
            )
        )

    test_cases: list[TestCase] = []

    for index in range(1, plan.test_cases + 1):
        requirement = requirements[(index - 1) % len(requirements)]

        component_id = requirement.target_component_id

        if component_id is None:
            raise ValueError("Handover requirement has no target component")

        created = BASE_TIME - timedelta(days=60 - index % 30)

        test_cases.append(
            TestCase(
                test_case_id=f"TC-NET-{index:06d}",
                title=(f"Verify online service after cellular handover #{index}"),
                description=("Switch cellular routes while an HCP3 online service is active."),
                test_type="Integration",
                expected_result=("The online service recovers after the network route changes."),
                priority="High",
                status="Approved",
                owner_team="ConnectivityValidation",
                version="1.0",
                requirement_ids=(requirement.requirement_id,),
                component_ids=(component_id,),
                target_ecu=catalog[component_id].ecu,
                created_at=created,
                updated_at=created + timedelta(days=5),
            )
        )

    execution_rng = random_for(
        plan.seed,
        "handover:executions",
    )

    failure_count = round(plan.test_executions * plan.failure_rate)

    failed_indices = set(
        execution_rng.sample(
            range(plan.test_executions),
            k=failure_count,
        )
    )

    executions: list[TestExecution] = []

    for index in range(plan.test_executions):
        failed = index in failed_indices

        start = BASE_TIME + timedelta(seconds=45 * index)

        if failed:
            duration_ms = execution_rng.randint(3_000, 6_000)
        else:
            duration_ms = execution_rng.randint(2_000, 4_000)

        executions.append(
            TestExecution(
                execution_id=(f"RUN-NH-20261001-{index + 1:06d}"),
                test_case_id=(test_cases[index % len(test_cases)].test_case_id),
                campaign_id="CAMP-NET-HANDOVER-202610",
                session_id=f"NH-SESSION-{index + 1:06d}",
                start_timestamp=start,
                end_timestamp=(start + timedelta(milliseconds=duration_ms)),
                result=(TestResult.FAIL if failed else TestResult.PASS),
                vehicle_id=f"VEH-{index % 25 + 1:04d}",
                software_version_hcp3="HCP3_3.4.0-B128",
                software_version_hcp5="HCP5_3.4.0-B094",
                software_version_conmod="CONMOD-R3.4.0",
                failure_reason=(
                    "Online service timed out after cellular handover." if failed else None
                ),
            )
        )

    defect_rng = random_for(
        plan.seed,
        "handover:defects",
    )

    failed_executions = [
        execution for execution in executions if execution.result == TestResult.FAIL
    ]

    defect_count = min(
        plan.defects,
        round(len(failed_executions) * plan.defect_probability_given_failure),
        len(failed_executions),
    )

    selected_failures = defect_rng.sample(
        failed_executions,
        k=defect_count,
    )

    case_by_id = {case.test_case_id: case for case in test_cases}

    defects: list[Defect] = []

    for index, execution in enumerate(
        selected_failures,
        start=1,
    ):
        test_case = case_by_id[execution.test_case_id]

        defects.append(
            Defect(
                defect_id=f"KPM-NH-{index:06d}",
                title=("Online service unavailable after cellular handover"),
                description=(
                    f"Online service timed out in "
                    f"{execution.execution_id} "
                    "after a network route change."
                ),
                severity="S2",
                priority="High",
                status="New",
                responsible_team="Connectivity",
                created_at=(execution.start_timestamp + timedelta(minutes=15)),
                updated_at=(execution.start_timestamp + timedelta(hours=2)),
                affected_ecu=ECU.HCP3,
                affected_component_id="SWC-HCP3-CONN-002",
                affected_software_version=(execution.software_version_hcp3),
                requirement_ids=test_case.requirement_ids,
                test_case_ids=(execution.test_case_id,),
                execution_ids=(execution.execution_id,),
                root_cause=("Online service did not recover after cellular network handover."),
            )
        )

    log_events: list[LogEvent] = []
    log_ids_by_execution: dict[str, list[str]] = {}

    if materialize_logs:
        for event in _iter_log_events(
            plan,
            executions,
        ):
            log_events.append(event)

            log_ids_by_execution.setdefault(
                event.execution_id,
                [],
            ).append(event.event_id)

    defect_by_execution = {
        execution_id: defect.defect_id
        for defect in defects
        for execution_id in defect.execution_ids
    }

    incidents = [
        Incident(
            incident_id=f"INC-NH-{index:06d}",
            scenario=SCENARIO_ID,
            execution_id=execution.execution_id,
            session_id=execution.session_id,
            failed=(execution.result == TestResult.FAIL),
            log_event_ids=tuple(
                log_ids_by_execution.get(
                    execution.execution_id,
                    (),
                )
            ),
            defect_id=defect_by_execution.get(execution.execution_id),
        )
        for index, execution in enumerate(
            executions,
            start=1,
        )
    ]

    traces = _generate_traces(
        plan,
        requirements,
        test_cases,
        executions,
        defects,
    )

    return GroundTruth(
        components=list(components),
        requirements=requirements,
        test_cases=test_cases,
        test_executions=executions,
        log_events=log_events,
        defects=defects,
        traces=traces,
        incidents=incidents,
    )


def iter_network_handover_log_batches(
    plan: NetworkHandoverPlan,
    executions: Sequence[TestExecution],
    batch_size: int,
) -> Iterator[list[LogEvent]]:
    """Stream deterministic batches of network-handover logs."""

    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    batch: list[LogEvent] = []

    for event in _iter_log_events(plan, executions):
        batch.append(event)

        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def _iter_log_events(
    plan: NetworkHandoverPlan,
    executions: Sequence[TestExecution],
) -> Iterator[LogEvent]:
    if not executions:
        return

    rng = random_for(
        plan.seed,
        "handover:logs",
    )

    additional, remainder = divmod(
        plan.log_events - len(executions) * 6,
        len(executions),
    )

    counter = 1

    for index, execution in enumerate(executions):
        if execution.end_timestamp is None:
            raise ValueError("Clean execution must have end_timestamp")

        failed = execution.result == TestResult.FAIL
        start = execution.start_timestamp

        events = [
            (
                0,
                ECU.CONMOD,
                "SWC-CON-CELL-002",
                "NETWORK_HANDOVER_START",
                LogSeverity.INFO,
                "Cellular network handover initiated.",
            ),
            (
                120,
                ECU.CONMOD,
                "SWC-CON-CELL-002",
                "CELLULAR_REGISTERED",
                LogSeverity.INFO,
                "Registered on target cellular network.",
            ),
            (
                250,
                ECU.CONMOD,
                "SRV-CON-NET-001",
                "NETWORK_ROUTE_READY",
                LogSeverity.INFO,
                "New network route available.",
            ),
            (
                400,
                ECU.HCP3,
                "SWC-HCP3-CONN-002",
                "ONLINE_SERVICE_REQUEST",
                LogSeverity.INFO,
                "Online service request sent after handover.",
            ),
        ]

        if failed:
            events.extend(
                [
                    (
                        950,
                        ECU.CONMOD,
                        "SWC-CON-BACKEND-004",
                        "BACKEND_UNREACHABLE",
                        LogSeverity.WARN,
                        "Backend remained unreachable after handover.",
                    ),
                    (
                        1500,
                        ECU.HCP3,
                        "SWC-HCP3-CONN-002",
                        "ONLINE_SERVICE_TIMEOUT",
                        LogSeverity.ERROR,
                        "Online service timed out after handover.",
                    ),
                ]
            )
        else:
            events.extend(
                [
                    (
                        900,
                        ECU.CONMOD,
                        "SWC-CON-BACKEND-004",
                        "BACKEND_RESTORED",
                        LogSeverity.INFO,
                        "Backend communication recovered.",
                    ),
                    (
                        1400,
                        ECU.HCP3,
                        "SWC-HCP3-CONN-002",
                        "ONLINE_SERVICE_AVAILABLE",
                        LogSeverity.INFO,
                        "Online service available after handover.",
                    ),
                ]
            )

        duration_ms = int((execution.end_timestamp - start).total_seconds() * 1000)

        filler_count = additional + int(index < remainder)

        for _ in range(filler_count):
            component_id, ecu = rng.choice(
                (
                    ("SWC-CON-DIAG-003", ECU.CONMOD),
                    ("SRV-CON-NET-001", ECU.CONMOD),
                    ("SWC-HCP3-CONN-002", ECU.HCP3),
                )
            )

            events.append(
                (
                    rng.randint(10, duration_ms - 10),
                    ecu,
                    component_id,
                    rng.choice(
                        (
                            "HANDOVER_STATE_SAMPLE",
                            "NETWORK_HEARTBEAT",
                            "SERVICE_STATUS_SAMPLE",
                        )
                    ),
                    LogSeverity.DEBUG,
                    "Network state sampled during handover.",
                )
            )

        events.sort(key=lambda item: item[0])

        for (
            offset,
            ecu,
            component_id,
            event_type,
            severity,
            message,
        ) in events:
            version = (
                execution.software_version_hcp3
                if ecu == ECU.HCP3
                else execution.software_version_conmod
            )

            yield LogEvent(
                event_id=f"LOG-NH-{counter:09d}",
                timestamp=(start + timedelta(milliseconds=offset)),
                ecu=ecu,
                component_id=component_id,
                event_type=event_type,
                severity=severity,
                message=message,
                session_id=execution.session_id,
                execution_id=execution.execution_id,
                software_version=version,
            )

            counter += 1


def _generate_traces(
    plan: NetworkHandoverPlan,
    requirements: Sequence[Requirement],
    test_cases: Sequence[TestCase],
    executions: Sequence[TestExecution],
    defects: Sequence[Defect],
) -> list[TraceRelationship]:
    traces: list[TraceRelationship] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    def add(
        source_type: str,
        source_id: str,
        relation: str,
        target_type: str,
        target_id: str,
    ) -> None:
        if len(traces) >= plan.trace_relationships:
            return

        key = (
            source_type,
            source_id,
            relation,
            target_type,
            target_id,
        )

        if key in seen:
            return

        seen.add(key)

        traces.append(
            TraceRelationship(
                trace_id=f"TRACE-NH-{len(traces) + 1:07d}",
                source_type=source_type,
                source_id=source_id,
                relationship_type=relation,
                target_type=target_type,
                target_id=target_id,
            )
        )

    for requirement in requirements:
        if requirement.target_component_id:
            add(
                "Requirement",
                requirement.requirement_id,
                "allocated_to",
                "Component",
                requirement.target_component_id,
            )

    for case in test_cases:
        for requirement_id in case.requirement_ids:
            add(
                "TestCase",
                case.test_case_id,
                "verifies",
                "Requirement",
                requirement_id,
            )

        for component_id in case.component_ids:
            add(
                "TestCase",
                case.test_case_id,
                "depends_on",
                "Component",
                component_id,
            )

    for execution in executions:
        add(
            "TestExecution",
            execution.execution_id,
            "related_to",
            "TestCase",
            execution.test_case_id,
        )

    for defect in defects:
        for execution_id in defect.execution_ids:
            add(
                "Defect",
                defect.defect_id,
                "generated_by",
                "TestExecution",
                execution_id,
            )

    for execution in executions:
        for component_id in HANDOVER_COMPONENT_IDS:
            add(
                "TestExecution",
                execution.execution_id,
                "related_to",
                "Component",
                component_id,
            )

    if len(traces) < plan.trace_relationships:
        raise ValueError(
            f"Requested {plan.trace_relationships} traces "
            f"but only {len(traces)} meaningful links exist"
        )

    return traces


def _validate(
    plan: NetworkHandoverPlan,
    components: Sequence[Component],
) -> None:
    quantities = (
        plan.requirements,
        plan.test_cases,
        plan.test_executions,
        plan.log_events,
        plan.defects,
        plan.trace_relationships,
    )

    if any(
        isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in quantities
    ):
        raise ValueError("Counts must be non-negative integers")

    if (
        min(
            plan.requirements,
            plan.test_cases,
            plan.test_executions,
        )
        == 0
    ):
        raise ValueError("At least one requirement, case and execution is required")

    if plan.log_events < plan.test_executions * 6:
        raise ValueError("Each execution requires at least six log events")

    for probability in (
        plan.failure_rate,
        plan.defect_probability_given_failure,
    ):
        if not 0 <= probability <= 1:
            raise ValueError("Probabilities must be between 0 and 1")

    catalog = {component.component_id: component for component in components}

    missing = set(HANDOVER_COMPONENT_IDS) - set(catalog)

    if missing:
        raise ValueError(f"Missing handover components: {sorted(missing)}")

    for component_id in HANDOVER_COMPONENT_IDS:
        expected_ecu = ECU.HCP3 if component_id.startswith("SWC-HCP3") else ECU.CONMOD

        if catalog[component_id].ecu != expected_ecu:
            raise ValueError(f"Incorrect ECU for {component_id}")
