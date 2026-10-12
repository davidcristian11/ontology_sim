"""Reusable clean-data generator for V2 engineering scenarios."""

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

BASE_TIME = datetime(2026, 10, 1, 8, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class ScenarioPlan:
    seed: int
    requirements: int
    test_cases: int
    test_executions: int
    log_events: int
    defects: int
    trace_relationships: int
    failure_rate: float = 0.16
    defect_probability_given_failure: float = 0.20


@dataclass(frozen=True, slots=True)
class EventStep:
    offset_ms: int
    ecu: ECU
    component_id: str
    event_type: str
    severity: LogSeverity
    message: str


@dataclass(frozen=True, slots=True)
class ScenarioSpec:
    scenario_id: str
    prefix: str
    requirements: tuple[tuple[str, str], ...]
    start_events: tuple[EventStep, ...]
    pass_events: tuple[EventStep, ...]
    fail_events: tuple[EventStep, ...]
    defect_title: str
    defect_component_id: str
    failure_reason: str
    filler_event_types: tuple[str, ...]
    failure_hcp3_version: str | None = None

    @property
    def component_ids(self) -> tuple[str, ...]:
        ids = [cid for _, cid in self.requirements]
        ids.extend(e.component_id for e in self.start_events)
        ids.extend(e.component_id for e in self.pass_events)
        ids.extend(e.component_id for e in self.fail_events)
        ids.append(self.defect_component_id)
        return tuple(dict.fromkeys(ids))


def generate_scenario_ground_truth(
    spec: ScenarioSpec,
    plan: ScenarioPlan,
    components: Sequence[Component],
    *,
    materialize_logs: bool = True,
) -> GroundTruth:
    _validate(spec, plan, components)

    catalog = {c.component_id: c for c in components}
    rng = random_for(plan.seed, f"{spec.scenario_id}:engineering")

    requirements = []

    for index in range(1, plan.requirements + 1):
        title, component_id = spec.requirements[(index - 1) % len(spec.requirements)]
        component = catalog[component_id]
        created = BASE_TIME - timedelta(days=rng.randint(30, 365))

        requirements.append(
            Requirement(
                requirement_id=f"REQ-{spec.prefix}-{index:06d}",
                title=f"{title} #{index}",
                description=f"{title}. Scenario: {spec.scenario_id}.",
                requirement_type="Functional",
                priority=rng.choice(("High", "Medium")),
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

    test_cases = []

    for index in range(1, plan.test_cases + 1):
        requirement = requirements[(index - 1) % len(requirements)]
        component_id = requirement.target_component_id

        if component_id is None:
            raise ValueError("Requirement has no target component")

        created = BASE_TIME - timedelta(days=60 - index % 30)

        test_cases.append(
            TestCase(
                test_case_id=f"TC-{spec.prefix}-{index:06d}",
                title=f"Verify {requirement.title}",
                description=f"Validate behavior: {spec.scenario_id}.",
                test_type="Integration",
                expected_result="System behavior matches the requirement.",
                priority="High",
                status="Approved",
                owner_team=catalog[component_id].owner_team,
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
        f"{spec.scenario_id}:executions",
    )

    failed_indices = set(
        execution_rng.sample(
            range(plan.test_executions),
            k=round(plan.test_executions * plan.failure_rate),
        )
    )

    executions = []

    for index in range(plan.test_executions):
        failed = index in failed_indices
        start = BASE_TIME + timedelta(seconds=index * 45)
        duration_ms = execution_rng.randint(3_000, 6_000)

        hcp3_version = (
            spec.failure_hcp3_version if failed and spec.failure_hcp3_version else "HCP3_3.4.0-B128"
        )

        executions.append(
            TestExecution(
                execution_id=(f"RUN-{spec.prefix}-20261001-{index + 1:06d}"),
                test_case_id=(test_cases[index % len(test_cases)].test_case_id),
                campaign_id=f"CAMP-{spec.prefix}-202610",
                session_id=f"SESSION-{spec.prefix}-{index + 1:06d}",
                start_timestamp=start,
                end_timestamp=(start + timedelta(milliseconds=duration_ms)),
                result=TestResult.FAIL if failed else TestResult.PASS,
                vehicle_id=f"VEH-{index % 25 + 1:04d}",
                software_version_hcp3=hcp3_version,
                software_version_hcp5="HCP5_3.4.0-B094",
                software_version_conmod="CONMOD-R3.4.0",
                failure_reason=spec.failure_reason if failed else None,
            )
        )

    defect_rng = random_for(
        plan.seed,
        f"{spec.scenario_id}:defects",
    )

    failed_executions = [e for e in executions if e.result == TestResult.FAIL]

    defect_count = min(
        plan.defects,
        round(len(failed_executions) * plan.defect_probability_given_failure),
        len(failed_executions),
    )

    selected = defect_rng.sample(
        failed_executions,
        k=defect_count,
    )

    case_by_id = {c.test_case_id: c for c in test_cases}
    affected_component = catalog[spec.defect_component_id]
    defects = []

    for index, execution in enumerate(selected, start=1):
        case = case_by_id[execution.test_case_id]

        versions = {
            ECU.HCP3: execution.software_version_hcp3,
            ECU.HCP5: execution.software_version_hcp5,
            ECU.CONMOD: execution.software_version_conmod,
        }

        defects.append(
            Defect(
                defect_id=f"KPM-{spec.prefix}-{index:06d}",
                title=spec.defect_title,
                description=(f"{spec.failure_reason} Execution: {execution.execution_id}."),
                severity="S2",
                priority="High",
                status="New",
                responsible_team=affected_component.owner_team,
                created_at=(execution.start_timestamp + timedelta(minutes=15)),
                updated_at=(execution.start_timestamp + timedelta(hours=2)),
                affected_ecu=affected_component.ecu,
                affected_component_id=spec.defect_component_id,
                affected_software_version=versions[affected_component.ecu],
                requirement_ids=case.requirement_ids,
                test_case_ids=(execution.test_case_id,),
                execution_ids=(execution.execution_id,),
                root_cause=spec.failure_reason,
            )
        )

    logs = []
    log_ids: dict[str, list[str]] = {}

    if materialize_logs:
        for event in _iter_events(spec, plan, executions):
            logs.append(event)
            log_ids.setdefault(
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
            incident_id=f"INC-{spec.prefix}-{i:06d}",
            scenario=spec.scenario_id,
            execution_id=e.execution_id,
            session_id=e.session_id,
            failed=e.result == TestResult.FAIL,
            log_event_ids=tuple(log_ids.get(e.execution_id, ())),
            defect_id=defect_by_execution.get(e.execution_id),
        )
        for i, e in enumerate(executions, 1)
    ]

    traces = _generate_traces(
        spec,
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
        log_events=logs,
        defects=defects,
        traces=traces,
        incidents=incidents,
    )


def iter_scenario_log_batches(
    spec: ScenarioSpec,
    plan: ScenarioPlan,
    executions: Sequence[TestExecution],
    batch_size: int,
) -> Iterator[list[LogEvent]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")

    batch = []

    for event in _iter_events(spec, plan, executions):
        batch.append(event)

        if len(batch) == batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def _iter_events(
    spec: ScenarioSpec,
    plan: ScenarioPlan,
    executions: Sequence[TestExecution],
) -> Iterator[LogEvent]:
    if not executions:
        return

    rng = random_for(plan.seed, f"{spec.scenario_id}:logs")

    mandatory = len(spec.start_events) + len(spec.pass_events)
    filler, remainder = divmod(
        plan.log_events - len(executions) * mandatory,
        len(executions),
    )

    event_counter = 1

    for index, execution in enumerate(executions):
        outcome = spec.fail_events if execution.result == TestResult.FAIL else spec.pass_events

        steps = (*spec.start_events, *outcome)

        local = [
            (
                step.offset_ms,
                step.ecu,
                step.component_id,
                step.event_type,
                step.severity,
                step.message,
            )
            for step in steps
        ]

        if execution.end_timestamp is None:
            raise ValueError("Clean execution must have end_timestamp")

        duration_ms = int(
            (execution.end_timestamp - execution.start_timestamp).total_seconds() * 1000
        )

        for _ in range(filler + int(index < remainder)):
            component_id = rng.choice(spec.component_ids)
            ecu = _component_ecu(component_id)
            event_type = rng.choice(spec.filler_event_types)

            local.append(
                (
                    rng.randint(10, duration_ms - 10),
                    ecu,
                    component_id,
                    event_type,
                    LogSeverity.DEBUG,
                    f"{event_type} during {spec.scenario_id}.",
                )
            )

        local.sort(key=lambda record: record[0])

        for offset, ecu, component_id, event_type, severity, message in local:
            version = {
                ECU.HCP3: execution.software_version_hcp3,
                ECU.HCP5: execution.software_version_hcp5,
                ECU.CONMOD: execution.software_version_conmod,
            }[ecu]

            yield LogEvent(
                event_id=f"LOG-{spec.prefix}-{event_counter:09d}",
                timestamp=(execution.start_timestamp + timedelta(milliseconds=offset)),
                ecu=ecu,
                component_id=component_id,
                event_type=event_type,
                severity=severity,
                message=message,
                session_id=execution.session_id,
                execution_id=execution.execution_id,
                software_version=version,
            )

            event_counter += 1


def _component_ecu(component_id: str) -> ECU:
    if component_id.startswith("SWC-HCP3-"):
        return ECU.HCP3
    if component_id.startswith("SWC-HCP5-"):
        return ECU.HCP5
    if component_id.startswith(("SWC-CON-", "SRV-CON-")):
        return ECU.CONMOD

    raise ValueError(f"Unrecognized component ID: {component_id}")


def _generate_traces(
    spec: ScenarioSpec,
    plan: ScenarioPlan,
    requirements: Sequence[Requirement],
    cases: Sequence[TestCase],
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

        key = (source_type, source_id, relation, target_type, target_id)

        if key in seen:
            return

        seen.add(key)

        traces.append(
            TraceRelationship(
                trace_id=f"TRACE-{spec.prefix}-{len(traces) + 1:07d}",
                source_type=source_type,
                source_id=source_id,
                relationship_type=relation,
                target_type=target_type,
                target_id=target_id,
            )
        )

    for req in requirements:
        if req.target_component_id:
            add(
                "Requirement",
                req.requirement_id,
                "allocated_to",
                "Component",
                req.target_component_id,
            )

    for case in cases:
        for req_id in case.requirement_ids:
            add("TestCase", case.test_case_id, "verifies", "Requirement", req_id)

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
        for component_id in spec.component_ids:
            add(
                "TestExecution",
                execution.execution_id,
                "related_to",
                "Component",
                component_id,
            )

    if len(traces) < plan.trace_relationships:
        raise ValueError(
            f"Not enough meaningful trace links for {spec.scenario_id}: "
            f"requested {plan.trace_relationships}, "
            f"available {len(traces)}"
        )

    return traces


def _validate(
    spec: ScenarioSpec,
    plan: ScenarioPlan,
    components: Sequence[Component],
) -> None:
    counts = (
        plan.requirements,
        plan.test_cases,
        plan.test_executions,
        plan.log_events,
        plan.defects,
        plan.trace_relationships,
    )

    if any(isinstance(n, bool) or not isinstance(n, int) or n < 0 for n in counts):
        raise ValueError("Counts must be non-negative integers")

    if min(plan.requirements, plan.test_cases, plan.test_executions) == 0:
        raise ValueError("At least one requirement, test case and execution is required")

    for rate in (
        plan.failure_rate,
        plan.defect_probability_given_failure,
    ):
        if not 0 <= rate <= 1:
            raise ValueError("Probabilities must be between zero and one")

    if not spec.requirements or not spec.filler_event_types:
        raise ValueError("Scenario must contain requirements and filler event types")

    if len(spec.pass_events) != len(spec.fail_events):
        raise ValueError("PASS and FAIL must have equal mandatory event counts")

    mandatory = len(spec.start_events) + len(spec.pass_events)

    if plan.log_events < mandatory * plan.test_executions:
        raise ValueError(f"At least {mandatory} logs are needed per execution")

    all_steps = (
        *spec.start_events,
        *spec.pass_events,
        *spec.fail_events,
    )

    if max(step.offset_ms for step in all_steps) >= 3000:
        raise ValueError("Mandatory events must fit within shortest execution")

    catalog = {c.component_id: c for c in components}
    missing = set(spec.component_ids) - set(catalog)

    if missing:
        raise ValueError(f"Missing scenario components: {sorted(missing)}")

    for component_id in spec.component_ids:
        if catalog[component_id].ecu != _component_ecu(component_id):
            raise ValueError(f"Incorrect ECU for {component_id}")

    for step in all_steps:
        if step.ecu != _component_ecu(step.component_id):
            raise ValueError(f"Incorrect event ECU for {step.component_id}")
