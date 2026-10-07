from datetime import UTC, datetime, timedelta

from ontologysim.generator.models import GroundTruth

BASE_TRACE_TIME = datetime(
    2026,
    9,
    1,
    8,
    0,
    tzinfo=UTC,
)


def project_traces(
    ground_truth: GroundTruth,
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []

    for index, trace in enumerate(ground_truth.traces):
        created_at = BASE_TRACE_TIME + timedelta(minutes=index)

        records.append(
            {
                "trace_id": trace.trace_id,
                "source_type": trace.source_type,
                "source_id": trace.source_id,
                "relationship_type": trace.relationship_type,
                "target_type": trace.target_type,
                "target_id": trace.target_id,
                "trace_status": "Valid",
                "created_at": created_at.isoformat(),
                "updated_at": created_at.isoformat(),
                "source_system": "OntologySim Trace Export",
            }
        )

    return records
