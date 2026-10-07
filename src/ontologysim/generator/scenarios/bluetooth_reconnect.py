from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

from ontologysim.generator.config import GeneratorConfig
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

BASE_TIME = datetime(2026, 10, 1, 8, 0, tzinfo=UTC)


CORE_COMPONENTS = (
    (
        "SWC-HCP3-BT-001",
        "BluetoothConnectionManager",
        "SoftwareComponent",
        ECU.HCP3,
        "Controls Bluetooth connection and reconnection behavior.",
        "Connectivity",
    ),
    (
        "SWC-HCP3-CONN-002",
        "ConnectivityStatusService",
        "Service",
        ECU.HCP3,
        "Provides user-facing connectivity state.",
        "Connectivity",
    ),
    (
        "SWC-HCP3-MEDIA-003",
        "MediaSessionManager",
        "SoftwareComponent",
        ECU.HCP3,
        "Coordinates Bluetooth media sessions.",
        "Infotainment",
    ),
    (
        "SWC-HCP3-PROFILE-004",
        "UserProfileManager",
        "SoftwareComponent",
        ECU.HCP3,
        "Maintains user and paired-device context.",
        "Infotainment",
    ),
    (
        "SWC-HCP5-PWR-001",
        "VehiclePowerStateManager",
        "SoftwareComponent",
        ECU.HCP5,
        "Maintains vehicle power state.",
        "VehicleState",
    ),
    (
        "SWC-HCP5-WAKE-002",
        "WakeSleepCoordinator",
        "SoftwareComponent",
        ECU.HCP5,
        "Coordinates vehicle wake and sleep transitions.",
        "VehicleState",
    ),
    (
        "SWC-HCP5-STATE-003",
        "VehicleStateDistributor",
        "Service",
        ECU.HCP5,
        "Distributes vehicle-state changes to dependent ECUs.",
        "VehicleState",
    ),
    (
        "SWC-HCP5-ENERGY-004",
        "EnergyManagementService",
        "Service",
        ECU.HCP5,
        "Provides energy-management context.",
        "EnergyManagement",
    ),
    (
        "SRV-CON-NET-001",
        "ConnectivityService",
        "Service",
        ECU.CONMOD,
        "Provides external network connectivity state.",
        "Connectivity",
    ),
    (
        "SWC-CON-CELL-002",
        "CellularManager",
        "SoftwareComponent",
        ECU.CONMOD,
        "Controls cellular network registration.",
        "Connectivity",
    ),
    (
        "SWC-CON-DIAG-003",
        "NetworkDiagnosticsService",
        "Service",
        ECU.CONMOD,
        "Reports connectivity diagnostics.",
        "Diagnostics",
    ),
    (
        "SWC-CON-BACKEND-004",
        "BackendCommunicationService",
        "Service",
        ECU.CONMOD,
        "Maintains backend communication.",
        "Connectivity",
    ),
)


def generate_bluetooth_reconnect_ground_truth(
    config: GeneratorConfig,
    *,
    materialize_logs: bool = True,
) -> GroundTruth:
    _validate_profile(config)

    components = _generate_components(config)
    requirements = _generate_requirements(config, components)
    test_cases = _generate_test_cases(
        config,
        requirements,
        components,
    )
    executions = _generate_test_executions(
        config,
        test_cases,
    )

    if materialize_logs:
        log_events, log_ids_by_execution = _generate_logs(
            config,
            executions,
        )
    else:
        log_events = []
        log_ids_by_execution = {execution.execution_id: () for execution in executions}

    defects = _generate_defects(
        config,
        executions,
        requirements,
    )

    incidents = _generate_incidents(
        executions,
        log_ids_by_execution,
        defects,
    )

    traces = _generate_traces(
        config,
        requirements,
        components,
        test_cases,
        executions,
        defects,
    )

    return GroundTruth(
        requirements=requirements,
        components=components,
        test_cases=test_cases,
        test_executions=executions,
        log_events=log_events,
        defects=defects,
        traces=traces,
        incidents=incidents,
    )


def _validate_profile(
    config: GeneratorConfig,
) -> None:
    profile = config.profile

    if profile.components < 12:
        raise ValueError("Bluetooth scenario currently requires at least 12 components.")

    minimum_logs = profile.test_executions * 6

    if profile.log_events < minimum_logs:
        raise ValueError(
            f"log_events must be at least {minimum_logs} for the configured execution count."
        )


def _generate_components(
    config: GeneratorConfig,
) -> list[Component]:
    components: list[Component] = []

    for (
        component_id,
        name,
        component_type,
        ecu,
        responsibility,
        team,
    ) in CORE_COMPONENTS:
        components.append(
            Component(
                component_id=component_id,
                component_name=name,
                component_type=component_type,
                ecu=ecu,
                responsibility=responsibility,
                version="3.4.0",
                status="Active",
                owner_team=team,
            )
        )

    additional_count = config.profile.components - len(components)

    for index in range(
        1,
        additional_count + 1,
    ):
        ecu = (
            ECU.HCP3,
            ECU.HCP5,
            ECU.CONMOD,
        )[(index - 1) % 3]

        components.append(
            Component(
                component_id=f"SWC-AUX-{index:04d}",
                component_name=f"AuxiliaryComponent{index:04d}",
                component_type="SoftwareComponent",
                ecu=ecu,
                responsibility=("Supporting scenario functionality."),
                version="3.4.0",
                status="Active",
                owner_team="Platform",
            )
        )

    return components


def _generate_requirements(
    config: GeneratorConfig,
    components: list[Component],
) -> list[Requirement]:
    rng = random_for(
        config.seed,
        "requirements",
    )

    hcp3 = [component for component in components if component.ecu == ECU.HCP3]

    hcp5 = [component for component in components if component.ecu == ECU.HCP5]

    conmod = [component for component in components if component.ecu == ECU.CONMOD]

    requirement_templates = (
        "Bluetooth connection shall recover after vehicle wake-up",
        "Vehicle wake state shall be distributed to dependent ECUs",
        "Bluetooth reconnection shall begin after wake notification",
        "Connectivity state shall be available during reconnection",
        "Paired device information shall survive vehicle sleep",
        "Bluetooth reconnection timeout shall be detected",
        "User-facing connectivity state shall reflect Bluetooth status",
        "Wake transition shall preserve communication dependencies",
    )

    requirements: list[Requirement] = []

    for index in range(
        1,
        config.profile.requirements + 1,
    ):
        selector = (index - 1) % 4

        if selector == 0:
            requirement_id = f"REQ-SYS-{index:06d}"
            ecu = None
            candidate_components = components
            requirement_type = "System"

        elif selector == 1:
            requirement_id = f"REQ-HCP3-{index:06d}"
            ecu = ECU.HCP3
            candidate_components = hcp3
            requirement_type = "Software"

        elif selector == 2:
            requirement_id = f"REQ-HCP5-{index:06d}"
            ecu = ECU.HCP5
            candidate_components = hcp5
            requirement_type = "Functional"

        else:
            requirement_id = f"REQ-CON-{index:06d}"
            ecu = ECU.CONMOD
            candidate_components = conmod
            requirement_type = "Interface"

        component = rng.choice(candidate_components)

        template = requirement_templates[(index - 1) % len(requirement_templates)]

        created_at = BASE_TIME - timedelta(
            days=rng.randint(
                30,
                720,
            )
        )

        requirements.append(
            Requirement(
                requirement_id=requirement_id,
                title=f"{template} #{index}",
                description=(
                    f"{template}. Requirement generated "
                    "for the Bluetooth wake-up "
                    "reconnection scenario."
                ),
                requirement_type=requirement_type,
                priority=rng.choice(
                    (
                        "High",
                        "Medium",
                        "Low",
                    )
                ),
                status="Approved",
                owner_team=component.owner_team,
                version="1.0",
                created_at=created_at,
                updated_at=(
                    created_at
                    + timedelta(
                        days=rng.randint(
                            1,
                            30,
                        )
                    )
                ),
                target_ecu=ecu,
                target_component_id=(component.component_id),
                verification_method="Test",
            )
        )

    return requirements


def _generate_test_cases(
    config: GeneratorConfig,
    requirements: list[Requirement],
    components: list[Component],
) -> list[TestCase]:
    rng = random_for(
        config.seed,
        "test_cases",
    )

    test_templates = (
        "Reconnect paired phone after normal vehicle wake",
        "Reconnect Bluetooth after short sleep cycle",
        "Reconnect Bluetooth while external connectivity initializes",
        "Verify Bluetooth retry after delayed wake-state distribution",
        "Verify reconnect timeout handling",
        "Verify Bluetooth state after repeated sleep/wake cycle",
        "Verify reconnect with degraded connectivity",
        "Verify paired-device session restoration",
    )

    test_cases: list[TestCase] = []

    for index in range(
        1,
        config.profile.test_cases + 1,
    ):
        requirement = rng.choice(requirements)

        if requirement.target_component_id:
            component_id = requirement.target_component_id
        else:
            component_id = rng.choice(components).component_id

        target_component = next(
            component for component in components if component.component_id == component_id
        )

        created_at = BASE_TIME - timedelta(days=90 - (index % 60))

        test_cases.append(
            TestCase(
                test_case_id=(f"TC-BT-{index:06d}"),
                title=test_templates[(index - 1) % len(test_templates)],
                description=(
                    "Validate Bluetooth reconnection "
                    "behavior following a vehicle "
                    "wake-up transition."
                ),
                test_type=rng.choice(
                    (
                        "Functional",
                        "Integration",
                        "Regression",
                        "System",
                    )
                ),
                expected_result=(
                    "Previously paired Bluetooth device reconnects within the allowed timeout."
                ),
                priority=rng.choice(
                    (
                        "High",
                        "Medium",
                    )
                ),
                status="Approved",
                owner_team=("ConnectivityValidation"),
                version="1.0",
                requirement_ids=(requirement.requirement_id,),
                component_ids=(component_id,),
                target_ecu=(target_component.ecu),
                created_at=created_at,
                updated_at=(
                    created_at
                    + timedelta(
                        days=rng.randint(
                            1,
                            20,
                        )
                    )
                ),
            )
        )

    return test_cases


def _generate_test_executions(
    config: GeneratorConfig,
    test_cases: list[TestCase],
) -> list[TestExecution]:
    rng = random_for(
        config.seed,
        "executions",
    )

    count = config.profile.test_executions

    failure_count = round(count * config.bluetooth_scenario.failure_rate)

    failed_indices = set(
        rng.sample(
            range(count),
            k=failure_count,
        )
        if failure_count
        else ()
    )

    executions: list[TestExecution] = []

    for index in range(count):
        sequence = index + 1

        test_case = rng.choice(test_cases)

        start = BASE_TIME + timedelta(seconds=index * 90)

        failed = index in failed_indices

        if failed:
            duration_ms = rng.randint(
                8_000,
                15_000,
            )

            result = TestResult.FAIL

            failure_reason = "Bluetooth reconnect timeout after vehicle wake-up."

        else:
            duration_ms = rng.randint(
                3_000,
                7_000,
            )

            result = TestResult.PASS
            failure_reason = None

        executions.append(
            TestExecution(
                execution_id=(f"RUN-20261001-{sequence:06d}"),
                test_case_id=(test_case.test_case_id),
                campaign_id=("CAMP-BT-WAKE-202610"),
                session_id=(f"SESSION-{sequence:06d}"),
                start_timestamp=start,
                end_timestamp=(start + timedelta(milliseconds=duration_ms)),
                result=result,
                vehicle_id=(f"VEH-{(index % 25) + 1:04d}"),
                software_version_hcp3=("HCP3_3.4.0-B128"),
                software_version_hcp5=("HCP5_3.4.0-B094"),
                software_version_conmod=("CONMOD-R3.4.0"),
                failure_reason=(failure_reason),
            )
        )

    return executions


def _generate_logs(
    config: GeneratorConfig,
    executions: list[TestExecution],
) -> tuple[
    list[LogEvent],
    dict[str, tuple[str, ...]],
]:
    logs: list[LogEvent] = []

    log_ids: dict[
        str,
        list[str],
    ] = {}

    for event in _iter_log_events(
        config,
        executions,
    ):
        logs.append(event)

        log_ids.setdefault(
            event.execution_id,
            [],
        ).append(event.event_id)

    return (
        logs,
        {execution_id: tuple(ids) for execution_id, ids in log_ids.items()},
    )


def iter_bluetooth_log_batches(
    config: GeneratorConfig,
    executions: list[TestExecution],
    batch_size: int,
) -> Iterator[list[LogEvent]]:
    if batch_size <= 0:
        raise ValueError("batch_size must be greater than zero")

    batch: list[LogEvent] = []

    for event in _iter_log_events(
        config,
        executions,
    ):
        batch.append(event)

        if len(batch) >= batch_size:
            yield batch
            batch = []

    if batch:
        yield batch


def _iter_log_events(
    config: GeneratorConfig,
    executions: list[TestExecution],
) -> Iterator[LogEvent]:
    rng = random_for(
        config.seed,
        "logs",
    )

    total_target = config.profile.log_events

    mandatory_total = len(executions) * 6

    filler_total = total_target - mandatory_total

    filler_per_execution, remainder = divmod(
        filler_total,
        len(executions),
    )

    event_counter = 1

    for execution_index, execution in enumerate(executions):
        local_events: list[
            tuple[
                datetime,
                ECU,
                str,
                str,
                LogSeverity,
                str,
                str,
            ]
        ] = []

        failed = execution.result == TestResult.FAIL

        local_events.extend(
            [
                (
                    execution.start_timestamp,
                    ECU.HCP5,
                    "SWC-HCP5-WAKE-002",
                    "VEHICLE_WAKE",
                    LogSeverity.INFO,
                    "Vehicle wake-up detected.",
                    execution.software_version_hcp5,
                ),
                (
                    (execution.start_timestamp + timedelta(milliseconds=80)),
                    ECU.HCP5,
                    "SWC-HCP5-STATE-003",
                    "POWER_STATE_AVAILABLE",
                    LogSeverity.INFO,
                    ("Vehicle power state changed to AWAKE."),
                    execution.software_version_hcp5,
                ),
                (
                    (execution.start_timestamp + timedelta(milliseconds=220)),
                    ECU.CONMOD,
                    "SRV-CON-NET-001",
                    "CONNECTIVITY_READY",
                    LogSeverity.INFO,
                    ("Connectivity service available after wake-up."),
                    (execution.software_version_conmod),
                ),
                (
                    (execution.start_timestamp + timedelta(milliseconds=350)),
                    ECU.HCP3,
                    "SWC-HCP3-BT-001",
                    "BT_RECONNECT_START",
                    LogSeverity.INFO,
                    ("Bluetooth reconnect started for paired device."),
                    execution.software_version_hcp3,
                ),
            ]
        )

        if failed:
            local_events.extend(
                [
                    (
                        (execution.start_timestamp + timedelta(milliseconds=1_500)),
                        ECU.HCP3,
                        "SWC-HCP3-BT-001",
                        "BT_RECONNECT_RETRY",
                        LogSeverity.WARN,
                        ("Bluetooth reconnect retry scheduled."),
                        (execution.software_version_hcp3),
                    ),
                    (
                        (execution.start_timestamp + timedelta(milliseconds=3_000)),
                        ECU.HCP3,
                        "SWC-HCP3-BT-001",
                        "BT_RECONNECT_TIMEOUT",
                        LogSeverity.ERROR,
                        ("Bluetooth reconnect timed out after vehicle wake-up."),
                        (execution.software_version_hcp3),
                    ),
                ]
            )

        else:
            local_events.extend(
                [
                    (
                        (execution.start_timestamp + timedelta(milliseconds=650)),
                        ECU.HCP3,
                        "SWC-HCP3-BT-001",
                        "BT_DEVICE_FOUND",
                        LogSeverity.INFO,
                        ("Previously paired Bluetooth device discovered."),
                        (execution.software_version_hcp3),
                    ),
                    (
                        (execution.start_timestamp + timedelta(milliseconds=900)),
                        ECU.HCP3,
                        "SWC-HCP3-BT-001",
                        "BT_RECONNECTED",
                        LogSeverity.INFO,
                        ("Bluetooth device reconnected successfully."),
                        (execution.software_version_hcp3),
                    ),
                ]
            )

        filler_count = filler_per_execution

        if execution_index < remainder:
            filler_count += 1

        if execution.end_timestamp is None:
            raise ValueError("Ground-truth execution must have an end timestamp.")

        duration_ms = int(
            (execution.end_timestamp - execution.start_timestamp).total_seconds() * 1000
        )

        filler_components = (
            (
                ECU.HCP3,
                "SWC-HCP3-CONN-002",
                (execution.software_version_hcp3),
            ),
            (
                ECU.HCP5,
                "SWC-HCP5-PWR-001",
                (execution.software_version_hcp5),
            ),
            (
                ECU.CONMOD,
                "SWC-CON-DIAG-003",
                (execution.software_version_conmod),
            ),
        )

        filler_types = (
            "STATE_SAMPLE",
            "SERVICE_HEARTBEAT",
            "SESSION_UPDATE",
            "DIAGNOSTIC_SAMPLE",
        )

        for _ in range(filler_count):
            (
                ecu,
                component_id,
                software_version,
            ) = rng.choice(filler_components)

            timestamp = execution.start_timestamp + timedelta(
                milliseconds=rng.randint(
                    10,
                    max(
                        11,
                        duration_ms - 10,
                    ),
                )
            )

            event_type = rng.choice(filler_types)

            local_events.append(
                (
                    timestamp,
                    ecu,
                    component_id,
                    event_type,
                    rng.choice(
                        (
                            LogSeverity.DEBUG,
                            LogSeverity.INFO,
                        )
                    ),
                    (f"{event_type} recorded during Bluetooth wake scenario."),
                    software_version,
                )
            )

        local_events.sort(key=lambda item: item[0])

        for (
            timestamp,
            ecu,
            component_id,
            event_type,
            severity,
            message,
            software_version,
        ) in local_events:
            yield LogEvent(
                event_id=(f"LOG-{event_counter:09d}"),
                timestamp=timestamp,
                ecu=ecu,
                component_id=component_id,
                event_type=event_type,
                severity=severity,
                message=message,
                session_id=(execution.session_id),
                execution_id=(execution.execution_id),
                software_version=(software_version),
            )

            event_counter += 1


def _generate_defects(
    config: GeneratorConfig,
    executions: list[TestExecution],
    requirements: list[Requirement],
) -> list[Defect]:
    rng = random_for(
        config.seed,
        "defects",
    )

    failed = [execution for execution in executions if execution.result == TestResult.FAIL]

    expected_defects = round(
        len(failed) * config.bluetooth_scenario.defect_probability_given_failure
    )

    defect_count = min(
        config.profile.defects,
        expected_defects,
        len(failed),
    )

    selected_executions = (
        rng.sample(
            failed,
            defect_count,
        )
        if defect_count
        else []
    )

    hcp3_requirements = [
        requirement for requirement in requirements if requirement.target_ecu == ECU.HCP3
    ]

    if not hcp3_requirements:
        hcp3_requirements = requirements

    defects: list[Defect] = []

    for index, execution in enumerate(
        selected_executions,
        start=1,
    ):
        requirement = rng.choice(hcp3_requirements)

        defects.append(
            Defect(
                defect_id=(f"KPM-{index:06d}"),
                title=("Bluetooth reconnect fails after vehicle wake-up"),
                description=(
                    "Bluetooth reconnection "
                    f"failed during "
                    f"{execution.execution_id}. "
                    "HCP5 wake state was "
                    "available but HCP3 did not "
                    "complete reconnection."
                ),
                severity=rng.choice(
                    (
                        "S2",
                        "S3",
                    )
                ),
                priority=rng.choice(
                    (
                        "High",
                        "Medium",
                    )
                ),
                status=rng.choice(
                    (
                        "New",
                        "Analysis",
                        "Assigned",
                    )
                ),
                responsible_team=("Connectivity"),
                created_at=(execution.start_timestamp + timedelta(minutes=20)),
                updated_at=(execution.start_timestamp + timedelta(hours=4)),
                affected_ecu=ECU.HCP3,
                affected_component_id=("SWC-HCP3-BT-001"),
                affected_software_version=(execution.software_version_hcp3),
                requirement_ids=(requirement.requirement_id,),
                test_case_ids=(execution.test_case_id,),
                execution_ids=(execution.execution_id,),
                root_cause=(
                    "Reconnect state machine did not complete after vehicle wake transition."
                ),
            )
        )

    return defects


def _generate_incidents(
    executions: list[TestExecution],
    log_ids_by_execution: dict[
        str,
        tuple[str, ...],
    ],
    defects: list[Defect],
) -> list[Incident]:
    defect_by_execution = {
        execution_id: defect.defect_id
        for defect in defects
        for execution_id in defect.execution_ids
    }

    incidents: list[Incident] = []

    for index, execution in enumerate(
        executions,
        start=1,
    ):
        incidents.append(
            Incident(
                incident_id=(f"INC-BT-{index:06d}"),
                scenario=("bluetooth_reconnect_after_wake"),
                execution_id=(execution.execution_id),
                session_id=(execution.session_id),
                failed=(execution.result == TestResult.FAIL),
                log_event_ids=(log_ids_by_execution[execution.execution_id]),
                defect_id=(defect_by_execution.get(execution.execution_id)),
            )
        )

    return incidents


def _generate_traces(
    config: GeneratorConfig,
    requirements: list[Requirement],
    components: list[Component],
    test_cases: list[TestCase],
    executions: list[TestExecution],
    defects: list[Defect],
) -> list[TraceRelationship]:
    rng = random_for(
        config.seed,
        "traces",
    )

    target_count = config.profile.trace_relationships

    traces: list[TraceRelationship] = []

    existing: set[
        tuple[
            str,
            str,
            str,
            str,
            str,
        ]
    ] = set()

    def add_trace(
        source_type: str,
        source_id: str,
        relationship_type: str,
        target_type: str,
        target_id: str,
    ) -> None:
        if len(traces) >= target_count:
            return

        key = (
            source_type,
            source_id,
            relationship_type,
            target_type,
            target_id,
        )

        if key in existing:
            return

        existing.add(key)

        traces.append(
            TraceRelationship(
                trace_id=(f"TRACE-{len(traces) + 1:07d}"),
                source_type=source_type,
                source_id=source_id,
                relationship_type=(relationship_type),
                target_type=target_type,
                target_id=target_id,
            )
        )

    for requirement in requirements:
        if requirement.target_component_id:
            add_trace(
                "Requirement",
                requirement.requirement_id,
                "allocated_to",
                "Component",
                (requirement.target_component_id),
            )

    for test_case in test_cases:
        for requirement_id in test_case.requirement_ids:
            add_trace(
                "TestCase",
                test_case.test_case_id,
                "verifies",
                "Requirement",
                requirement_id,
            )

        for component_id in test_case.component_ids:
            add_trace(
                "TestCase",
                test_case.test_case_id,
                "depends_on",
                "Component",
                component_id,
            )

    for execution in executions:
        add_trace(
            "TestExecution",
            execution.execution_id,
            "related_to",
            "TestCase",
            execution.test_case_id,
        )

    for defect in defects:
        for execution_id in defect.execution_ids:
            add_trace(
                "Defect",
                defect.defect_id,
                "generated_by",
                "TestExecution",
                execution_id,
            )

    attempts = 0
    maximum_attempts = target_count * 20

    while len(traces) < target_count and attempts < maximum_attempts:
        attempts += 1

        execution = rng.choice(executions)

        if rng.random() < 0.5:
            component = rng.choice(components)

            add_trace(
                "TestExecution",
                execution.execution_id,
                "related_to",
                "Component",
                component.component_id,
            )

        else:
            requirement = rng.choice(requirements)

            add_trace(
                "TestExecution",
                execution.execution_id,
                "related_to",
                "Requirement",
                requirement.requirement_id,
            )

    if len(traces) != target_count:
        raise RuntimeError(
            f"Could only generate {len(traces)} unique traces; requested {target_count}."
        )

    return traces
