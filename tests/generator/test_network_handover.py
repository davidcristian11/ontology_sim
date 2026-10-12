from collections import defaultdict

import pytest

from ontologysim.generator.models import (
    ECU,
    Component,
)
from ontologysim.generator.models import (
    TestResult as Result,
)
from ontologysim.generator.scenarios.network_handover import (
    HANDOVER_COMPONENT_IDS,
    NetworkHandoverPlan,
    generate_network_handover_ground_truth,
    iter_network_handover_log_batches,
)


def _components() -> list[Component]:
    entries = (
        ("SRV-CON-NET-001", "ConnectivityService", ECU.CONMOD),
        ("SWC-CON-CELL-002", "CellularManager", ECU.CONMOD),
        (
            "SWC-CON-BACKEND-004",
            "BackendCommunicationService",
            ECU.CONMOD,
        ),
        (
            "SWC-CON-DIAG-003",
            "NetworkDiagnosticsService",
            ECU.CONMOD,
        ),
        (
            "SWC-HCP3-CONN-002",
            "ConnectivityStatusService",
            ECU.HCP3,
        ),
    )

    return [
        Component(
            component_id=component_id,
            component_name=name,
            component_type="Service",
            ecu=ecu,
            responsibility="Connectivity support",
            version="3.4.0",
            status="Active",
            owner_team="Connectivity",
        )
        for component_id, name, ecu in entries
    ]


def _plan() -> NetworkHandoverPlan:
    return NetworkHandoverPlan(
        seed=20261001,
        requirements=7,
        test_cases=10,
        test_executions=40,
        log_events=450,
        defects=4,
        trace_relationships=100,
    )


def test_handover_clean_references_and_determinism() -> None:
    components = _components()
    plan = _plan()

    result = generate_network_handover_ground_truth(
        plan,
        components,
    )

    assert result == generate_network_handover_ground_truth(
        plan,
        components,
    )

    assert len(result.requirements) == 7
    assert len(result.test_cases) == 10
    assert len(result.test_executions) == 40
    assert len(result.log_events) == 450
    assert len(result.traces) == 100
    assert len(result.incidents) == 40

    component_ids = {item.component_id for item in result.components}

    requirement_ids = {item.requirement_id for item in result.requirements}

    case_ids = {item.test_case_id for item in result.test_cases}

    execution_ids = {item.execution_id for item in result.test_executions}

    log_ids = {item.event_id for item in result.log_events}

    assert set(HANDOVER_COMPONENT_IDS) <= component_ids

    assert all(item.target_component_id in component_ids for item in result.requirements)

    assert all(set(item.requirement_ids) <= requirement_ids for item in result.test_cases)

    assert all(set(item.component_ids) <= component_ids for item in result.test_cases)

    assert all(item.test_case_id in case_ids for item in result.test_executions)

    assert all(
        item.execution_id in execution_ids and item.component_id in component_ids
        for item in result.log_events
    )

    assert all(
        item.execution_ids and set(item.execution_ids) <= execution_ids for item in result.defects
    )

    assert all(set(item.log_event_ids) <= log_ids for item in result.incidents)


def test_handover_pass_and_fail_evidence() -> None:
    result = generate_network_handover_ground_truth(
        _plan(),
        _components(),
    )

    by_execution: dict[str, set[str]] = defaultdict(set)

    for event in result.log_events:
        by_execution[event.execution_id].add(event.event_type)

    assert {execution.result for execution in result.test_executions} == {Result.PASS, Result.FAIL}

    for execution in result.test_executions:
        events = by_execution[execution.execution_id]

        assert {
            "NETWORK_HANDOVER_START",
            "ONLINE_SERVICE_REQUEST",
        } <= events

        if execution.result == Result.FAIL:
            assert {
                "BACKEND_UNREACHABLE",
                "ONLINE_SERVICE_TIMEOUT",
            } <= events
        else:
            assert {
                "BACKEND_RESTORED",
                "ONLINE_SERVICE_AVAILABLE",
            } <= events

    failed_execution_ids = {
        execution.execution_id
        for execution in result.test_executions
        if execution.result == Result.FAIL
    }

    assert all(set(defect.execution_ids) <= failed_execution_ids for defect in result.defects)


def test_streaming_is_chunk_size_independent() -> None:
    plan = _plan()

    clean = generate_network_handover_ground_truth(
        plan,
        _components(),
    )

    for size in (17, 89):
        batches = list(
            iter_network_handover_log_batches(
                plan,
                clean.test_executions,
                size,
            )
        )

        assert max(map(len, batches)) <= size

        streamed = [event for batch in batches for event in batch]

        assert streamed == clean.log_events

    no_logs = generate_network_handover_ground_truth(
        plan,
        _components(),
        materialize_logs=False,
    )

    assert not no_logs.log_events


def test_handover_rejects_missing_components() -> None:
    with pytest.raises(
        ValueError,
        match="Missing handover components",
    ):
        generate_network_handover_ground_truth(
            _plan(),
            _components()[:2],
        )
