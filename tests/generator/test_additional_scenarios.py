import pytest

from ontologysim.generator.models import ECU, Component
from ontologysim.generator.models import TestResult as Result
from ontologysim.generator.scenarios import (
    charging_failure,
    extended_awake,
    infotainment_startup,
    poor_connectivity,
    software_compatibility,
    stale_navigation,
)
from ontologysim.generator.scenarios.scenario_components import (
    extend_component_catalog,
)
from ontologysim.generator.scenarios.shared_scenario import (
    ScenarioPlan,
    generate_scenario_ground_truth,
    iter_scenario_log_batches,
)

SPECS = [
    module.SPEC
    for module in (
        charging_failure,
        infotainment_startup,
        stale_navigation,
        extended_awake,
        software_compatibility,
        poor_connectivity,
    )
]


def _components() -> list[Component]:
    existing = {
        "SWC-HCP5-ENERGY-004": ECU.HCP5,
        "SWC-HCP5-WAKE-002": ECU.HCP5,
        "SWC-HCP5-STATE-003": ECU.HCP5,
        "SWC-HCP3-MEDIA-003": ECU.HCP3,
        "SWC-HCP3-CONN-002": ECU.HCP3,
        "SRV-CON-NET-001": ECU.CONMOD,
        "SWC-CON-BACKEND-004": ECU.CONMOD,
        "SWC-CON-DIAG-003": ECU.CONMOD,
        "SWC-CON-CELL-002": ECU.CONMOD,
    }

    base = [
        Component(
            component_id=identifier,
            component_name=identifier,
            component_type="Service",
            ecu=ecu,
            responsibility="Test component",
            version="3.4.0",
            status="Active",
            owner_team="Test",
        )
        for identifier, ecu in existing.items()
    ]

    return extend_component_catalog(base)


@pytest.mark.parametrize(
    "spec",
    SPECS,
    ids=lambda spec: spec.scenario_id,
)
def test_additional_scenario(spec) -> None:
    plan = ScenarioPlan(
        seed=20261001,
        requirements=5,
        test_cases=8,
        test_executions=40,
        log_events=450,
        defects=4,
        trace_relationships=100,
    )

    components = _components()

    result = generate_scenario_ground_truth(
        spec,
        plan,
        components,
    )

    # Determinism
    assert result == generate_scenario_ground_truth(
        spec,
        plan,
        components,
    )

    assert len(result.requirements) == 5
    assert len(result.test_cases) == 8
    assert len(result.test_executions) == 40
    assert len(result.log_events) == 450
    assert len(result.traces) == 100
    assert len(result.incidents) == 40

    requirement_ids = {item.requirement_id for item in result.requirements}
    component_ids = {item.component_id for item in result.components}
    test_case_ids = {item.test_case_id for item in result.test_cases}
    execution_ids = {item.execution_id for item in result.test_executions}

    # Clean relationships
    assert all(item.target_component_id in component_ids for item in result.requirements)

    assert all(
        set(item.requirement_ids) <= requirement_ids and set(item.component_ids) <= component_ids
        for item in result.test_cases
    )

    assert all(item.test_case_id in test_case_ids for item in result.test_executions)

    assert all(
        item.execution_id in execution_ids and item.component_id in component_ids
        for item in result.log_events
    )

    assert all(set(item.execution_ids) <= execution_ids for item in result.defects)

    assert {item.result for item in result.test_executions} == {Result.PASS, Result.FAIL}

    # Streaming must not change the generated logs.
    for chunk_size in (19, 73):
        streamed = [
            event
            for batch in iter_scenario_log_batches(
                spec,
                plan,
                result.test_executions,
                chunk_size,
            )
            for event in batch
        ]

        assert streamed == result.log_events

    # Streaming mode does not materialize logs.
    no_logs = generate_scenario_ground_truth(
        spec,
        plan,
        components,
        materialize_logs=False,
    )

    assert no_logs.log_events == []


def test_v2_catalog_does_not_duplicate_components() -> None:
    components = _components()

    extended = extend_component_catalog(components)

    assert len(extended) == len(components)


def test_software_compatibility_has_version_difference() -> None:
    plan = ScenarioPlan(
        seed=20261001,
        requirements=5,
        test_cases=8,
        test_executions=40,
        log_events=450,
        defects=4,
        trace_relationships=100,
    )

    result = generate_scenario_ground_truth(
        software_compatibility.SPEC,
        plan,
        _components(),
        materialize_logs=False,
    )

    failed = [execution for execution in result.test_executions if execution.result == Result.FAIL]

    passed = [execution for execution in result.test_executions if execution.result == Result.PASS]

    assert all(execution.software_version_hcp3 == "HCP3_3.5.0-B201" for execution in failed)

    assert all(execution.software_version_hcp3 == "HCP3_3.4.0-B128" for execution in passed)
