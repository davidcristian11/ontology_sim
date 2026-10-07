from dataclasses import replace

from ontologysim.generator.config import (
    ProfileConfig,
    load_generator_config,
)
from ontologysim.generator.pipeline import generate_ground_truth


def test_ground_truth_references_existing_entities() -> None:
    config = load_generator_config("config/generator.toml")

    profile = ProfileConfig(
        requirements=12,
        components=12,
        test_cases=12,
        test_executions=30,
        log_events=600,
        defects=3,
        trace_relationships=80,
    )

    config = replace(config, profile=profile)

    ground_truth = generate_ground_truth(config)

    requirement_ids = {item.requirement_id for item in ground_truth.requirements}

    component_ids = {item.component_id for item in ground_truth.components}

    test_case_ids = {item.test_case_id for item in ground_truth.test_cases}

    execution_ids = {item.execution_id for item in ground_truth.test_executions}

    log_ids = {item.event_id for item in ground_truth.log_events}

    defect_ids = {item.defect_id for item in ground_truth.defects}

    for requirement in ground_truth.requirements:
        if requirement.target_component_id is not None:
            assert requirement.target_component_id in component_ids

    for test_case in ground_truth.test_cases:
        assert set(test_case.requirement_ids) <= requirement_ids
        assert set(test_case.component_ids) <= component_ids

    for execution in ground_truth.test_executions:
        assert execution.test_case_id in test_case_ids

    for log in ground_truth.log_events:
        assert log.execution_id in execution_ids
        assert log.component_id in component_ids

    for defect in ground_truth.defects:
        assert set(defect.requirement_ids) <= requirement_ids
        assert set(defect.test_case_ids) <= test_case_ids
        assert set(defect.execution_ids) <= execution_ids
        assert defect.affected_component_id in component_ids

    for incident in ground_truth.incidents:
        assert incident.execution_id in execution_ids
        assert set(incident.log_event_ids) <= log_ids

        if incident.defect_id is not None:
            assert incident.defect_id in defect_ids
