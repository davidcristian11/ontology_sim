from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum


class ECU(StrEnum):
    HCP3 = "HCP3"
    HCP5 = "HCP5"
    CONMOD = "ConMod"


class TestResult(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    ERROR = "ERROR"
    BLOCKED = "BLOCKED"
    NOT_EXECUTED = "NOT_EXECUTED"


class LogSeverity(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


@dataclass(frozen=True, slots=True)
class Requirement:
    requirement_id: str
    title: str
    description: str
    requirement_type: str
    priority: str
    status: str
    owner_team: str
    version: str
    created_at: datetime
    updated_at: datetime
    target_ecu: ECU | None = None
    target_component_id: str | None = None
    parent_requirement_id: str | None = None
    related_requirement_ids: tuple[str, ...] = ()
    verification_method: str | None = None


@dataclass(frozen=True, slots=True)
class Component:
    component_id: str
    component_name: str
    component_type: str
    ecu: ECU
    responsibility: str
    version: str
    status: str
    owner_team: str
    parent_component_id: str | None = None


@dataclass(frozen=True, slots=True)
class TestCase:
    test_case_id: str
    title: str
    description: str
    test_type: str
    expected_result: str
    priority: str
    status: str
    owner_team: str
    version: str
    requirement_ids: tuple[str, ...]
    component_ids: tuple[str, ...]
    target_ecu: ECU
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class TestExecution:
    execution_id: str
    test_case_id: str
    campaign_id: str
    session_id: str
    start_timestamp: datetime
    end_timestamp: datetime | None
    result: TestResult
    vehicle_id: str
    software_version_hcp3: str
    software_version_hcp5: str
    software_version_conmod: str
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class LogEvent:
    event_id: str
    timestamp: datetime
    ecu: ECU
    component_id: str
    event_type: str
    severity: LogSeverity
    message: str
    session_id: str
    execution_id: str
    software_version: str


@dataclass(frozen=True, slots=True)
class Defect:
    defect_id: str
    title: str
    description: str
    severity: str
    priority: str
    status: str
    responsible_team: str
    created_at: datetime
    updated_at: datetime
    affected_ecu: ECU
    affected_component_id: str
    affected_software_version: str
    requirement_ids: tuple[str, ...]
    test_case_ids: tuple[str, ...]
    execution_ids: tuple[str, ...]
    root_cause: str | None = None


@dataclass(frozen=True, slots=True)
class TraceRelationship:
    trace_id: str
    source_type: str
    source_id: str
    relationship_type: str
    target_type: str
    target_id: str


@dataclass(frozen=True, slots=True)
class Incident:
    incident_id: str
    scenario: str
    execution_id: str
    session_id: str
    failed: bool
    log_event_ids: tuple[str, ...]
    defect_id: str | None = None


@dataclass(slots=True)
class GroundTruth:
    requirements: list[Requirement] = field(default_factory=list)
    components: list[Component] = field(default_factory=list)
    test_cases: list[TestCase] = field(default_factory=list)
    test_executions: list[TestExecution] = field(default_factory=list)
    log_events: list[LogEvent] = field(default_factory=list)
    defects: list[Defect] = field(default_factory=list)
    traces: list[TraceRelationship] = field(default_factory=list)
    incidents: list[Incident] = field(default_factory=list)
