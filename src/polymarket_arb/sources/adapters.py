from polymarket_arb.domain.models import SourceEventRecord
from polymarket_arb.sources.models import SourceDefinition


def normalize_http_json_payload(
    *,
    definition: SourceDefinition,
    payload: dict[str, object],
    received_timestamp_ms: int,
    affected_market_ids: list[str],
) -> SourceEventRecord:
    return SourceEventRecord(
        source_event_id=f"{definition.key}:{received_timestamp_ms}",
        source_type=definition.source_type,
        source_key=definition.key,
        received_timestamp_ms=received_timestamp_ms,
        normalized_payload=dict(payload),
        affected_market_ids=affected_market_ids,
    )
