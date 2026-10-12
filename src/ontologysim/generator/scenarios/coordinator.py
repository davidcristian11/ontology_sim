"""Combine eight scenarios into one clean engineering dataset.

This module does not write files or modify the V1 pipeline.
"""

from collections.abc import Iterator
from dataclasses import dataclass, replace

from ontologysim.generator.config import GeneratorConfig
from ontologysim.generator.models import GroundTruth, LogEvent
from ontologysim.generator.scenarios import (
    charging_failure,
    extended_awake,
    infotainment_startup,
    poor_connectivity,
    software_compatibility,
    stale_navigation,
)
from ontologysim.generator.scenarios.bluetooth_reconnect import (
    generate_bluetooth_reconnect_ground_truth,
    iter_bluetooth_log_batches,
)
from ontologysim.generator.scenarios.network_handover import (
    NetworkHandoverPlan,
    generate_network_handover_ground_truth,
    iter_network_handover_log_batches,
)
from ontologysim.generator.scenarios.registry import (
    SCENARIOS,
    allocate_test_executions,
)
from ontologysim.generator.scenarios.scenario_components import (
    EXTRA_COMPONENTS,
    extend_component_catalog,
)
from ontologysim.generator.scenarios.shared_scenario import (
    ScenarioPlan,
    ScenarioSpec,
    generate_scenario_ground_truth,
    iter_scenario_log_batches,
)

BLUETOOTH = "bluetooth_reconnect_after_wake"
HANDOVER = "online_service_network_handover"

SHARED_SPECS: dict[str, ScenarioSpec] = {
    spec.scenario_id: spec
    for spec in (
        charging_failure.SPEC,
        infotainment_startup.SPEC,
        stale_navigation.SPEC,
        extended_awake.SPEC,
        software_compatibility.SPEC,
        poor_connectivity.SPEC,
    )
}

ALLOCATED_FIELDS = (
    "requirements",
    "test_cases",
    "test_executions",
    "log_events",
    "defects",
    "trace_relationships",
)


@dataclass(slots=True)
class ScenarioRun:
    scenario_id: str
    ground_truth: GroundTruth
    plan: ScenarioPlan | NetworkHandoverPlan | None = None
    bluetooth_config: GeneratorConfig | None = None


@dataclass(slots=True)
class MultiScenarioResult:
    ground_truth: GroundTruth
    runs: tuple[ScenarioRun, ...]
    allocations: dict[str, dict[str, int]]


def build_multi_scenario_ground_truth(
    config: GeneratorConfig,
    *,
    materialize_logs: bool = False,
) -> MultiScenarioResult:
    """Generate all configured scenario slices and merge them."""

    weights = dict(config.scenario_weights)

    if not weights:
        raise ValueError("Multi-scenario weights are missing")

    unknown = set(weights) - set(SCENARIOS)

    if unknown:
        raise ValueError(f"Unknown scenarios: {sorted(unknown)}")

    active = [name for name in SCENARIOS if weights.get(name, 0) > 0]

    if BLUETOOTH not in active:
        raise ValueError("V2 currently requires Bluetooth as the base scenario")

    allocations = {
        field_name: allocate_test_executions(
            getattr(config.profile, field_name),
            weights,
            seed=config.seed + index,
        )
        for index, field_name in enumerate(ALLOCATED_FIELDS)
    }

    def count(field_name: str, scenario_id: str) -> int:
        return allocations[field_name][scenario_id]

    for scenario_id in active:
        for field_name in (
            "requirements",
            "test_cases",
            "test_executions",
            "trace_relationships",
        ):
            if count(field_name, scenario_id) <= 0:
                raise ValueError(
                    f"{scenario_id} received no {field_name}; "
                    "increase the profile or adjust weights"
                )

        if count("log_events", scenario_id) < (6 * count("test_executions", scenario_id)):
            raise ValueError(f"Insufficient logs for {scenario_id}")

    # V1 Bluetooth generation remains unchanged.
    # Reserve component capacity for V2 named components.
    base_component_count = max(
        12,
        config.profile.components - len(EXTRA_COMPONENTS),
    )

    bluetooth_profile = replace(
        config.profile,
        components=base_component_count,
        **{field_name: count(field_name, BLUETOOTH) for field_name in ALLOCATED_FIELDS},
    )

    bluetooth_config = replace(
        config,
        scenario_name=BLUETOOTH,
        profile=bluetooth_profile,
    )

    bluetooth_gt = generate_bluetooth_reconnect_ground_truth(
        bluetooth_config,
        materialize_logs=materialize_logs,
    )

    components = extend_component_catalog(bluetooth_gt.components)

    runs = [
        ScenarioRun(
            scenario_id=BLUETOOTH,
            ground_truth=bluetooth_gt,
            bluetooth_config=bluetooth_config,
        )
    ]

    for scenario_id in active:
        if scenario_id == BLUETOOTH:
            continue

        common_arguments = {
            "seed": config.seed,
            **{field_name: count(field_name, scenario_id) for field_name in ALLOCATED_FIELDS},
        }

        if scenario_id == HANDOVER:
            handover_plan = NetworkHandoverPlan(**common_arguments)

            ground_truth = generate_network_handover_ground_truth(
                handover_plan,
                components,
                materialize_logs=materialize_logs,
            )

            runs.append(
                ScenarioRun(
                    scenario_id=scenario_id,
                    ground_truth=ground_truth,
                    plan=handover_plan,
                )
            )

        else:
            spec = SHARED_SPECS[scenario_id]

            plan = ScenarioPlan(**common_arguments)

            ground_truth = generate_scenario_ground_truth(
                spec,
                plan,
                components,
                materialize_logs=materialize_logs,
            )

            runs.append(
                ScenarioRun(
                    scenario_id=scenario_id,
                    ground_truth=ground_truth,
                    plan=plan,
                )
            )

    combined = GroundTruth(
        components=components,
        requirements=[item for run in runs for item in run.ground_truth.requirements],
        test_cases=[item for run in runs for item in run.ground_truth.test_cases],
        test_executions=[item for run in runs for item in run.ground_truth.test_executions],
        log_events=[item for run in runs for item in run.ground_truth.log_events],
        defects=[item for run in runs for item in run.ground_truth.defects],
        traces=[item for run in runs for item in run.ground_truth.traces],
        incidents=[item for run in runs for item in run.ground_truth.incidents],
    )

    _validate_merged_references(combined)

    return MultiScenarioResult(
        ground_truth=combined,
        runs=tuple(runs),
        allocations=allocations,
    )


def iter_multi_scenario_log_batches(
    result: MultiScenarioResult,
    batch_size: int,
) -> Iterator[list[LogEvent]]:
    """Stream scenario logs without materializing all events."""

    for run in result.runs:
        if run.scenario_id == BLUETOOTH:
            if run.bluetooth_config is None:
                raise RuntimeError("Missing Bluetooth config")

            yield from iter_bluetooth_log_batches(
                run.bluetooth_config,
                run.ground_truth.test_executions,
                batch_size,
            )

        elif run.scenario_id == HANDOVER:
            if not isinstance(run.plan, NetworkHandoverPlan):
                raise RuntimeError("Missing handover plan")

            yield from iter_network_handover_log_batches(
                run.plan,
                run.ground_truth.test_executions,
                batch_size,
            )

        else:
            if not isinstance(run.plan, ScenarioPlan):
                raise RuntimeError(f"Missing plan for {run.scenario_id}")

            yield from iter_scenario_log_batches(
                SHARED_SPECS[run.scenario_id],
                run.plan,
                run.ground_truth.test_executions,
                batch_size,
            )


def _validate_merged_references(
    ground_truth: GroundTruth,
) -> None:
    """Reject duplicate identities and broken clean references."""

    entity_groups = {
        "Component": (
            ground_truth.components,
            "component_id",
        ),
        "Requirement": (
            ground_truth.requirements,
            "requirement_id",
        ),
        "TestCase": (
            ground_truth.test_cases,
            "test_case_id",
        ),
        "TestExecution": (
            ground_truth.test_executions,
            "execution_id",
        ),
        "LogEvent": (
            ground_truth.log_events,
            "event_id",
        ),
        "Defect": (
            ground_truth.defects,
            "defect_id",
        ),
        "TraceRelationship": (
            ground_truth.traces,
            "trace_id",
        ),
        "Incident": (
            ground_truth.incidents,
            "incident_id",
        ),
    }

    identifiers: dict[str, set[str]] = {}

    for entity_name, (records, id_field) in entity_groups.items():
        values = [getattr(record, id_field) for record in records]

        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate clean {entity_name} IDs")

        identifiers[entity_name] = set(values)

    def check(
        entity_name: str,
        identifier: str,
    ) -> None:
        if identifier not in identifiers[entity_name]:
            raise ValueError(f"Missing {entity_name} reference: {identifier}")

    for requirement in ground_truth.requirements:
        if requirement.target_component_id:
            check(
                "Component",
                requirement.target_component_id,
            )

    for case in ground_truth.test_cases:
        for req_id in case.requirement_ids:
            check("Requirement", req_id)

        for component_id in case.component_ids:
            check("Component", component_id)

    for execution in ground_truth.test_executions:
        check("TestCase", execution.test_case_id)

    for defect in ground_truth.defects:
        check("Component", defect.affected_component_id)

        for execution_id in defect.execution_ids:
            check("TestExecution", execution_id)

        for req_id in defect.requirement_ids:
            check("Requirement", req_id)

        for case_id in defect.test_case_ids:
            check("TestCase", case_id)

    for event in ground_truth.log_events:
        check("Component", event.component_id)
        check("TestExecution", event.execution_id)

    for incident in ground_truth.incidents:
        check("TestExecution", incident.execution_id)

        if incident.defect_id is not None:
            check("Defect", incident.defect_id)

        for log_id in incident.log_event_ids:
            check("LogEvent", log_id)

    for trace in ground_truth.traces:
        for entity_type, entity_id in (
            (trace.source_type, trace.source_id),
            (trace.target_type, trace.target_id),
        ):
            if entity_type not in identifiers:
                raise ValueError(f"Unknown trace entity type: {entity_type}")

            check(entity_type, entity_id)
