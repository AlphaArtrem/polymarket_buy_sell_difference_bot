import json
from pathlib import Path
from typing import Any, Dict

from polymarket_arb.domain.models import MarketCatalogEntry


def _serialize_payload(payload: Any) -> Any:
    if hasattr(payload, "model_dump"):
        return payload.model_dump()
    if isinstance(payload, list):
        return [_serialize_payload(item) for item in payload]
    if isinstance(payload, dict):
        return {key: _serialize_payload(value) for key, value in payload.items()}
    return payload


def write_run_summary(output_dir: Path, summary: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return summary_path


def write_catalog_snapshot(output_path: Path, catalog: list[MarketCatalogEntry]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([entry.model_dump() for entry in catalog], indent=2) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_latency_summary(output_path: Path, payload: Dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def write_feed_health(output_path: Path, payload: Dict[str, Any]) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return output_path


def write_opportunity_summary(output_dir: Path, payload: Any) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "opportunity_summary.json"
    data = _serialize_payload(payload)
    summary_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return summary_path


def write_market_quality_summary(output_dir: Path, payload: Any) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "market_quality_summary.json"
    data = _serialize_payload(payload)
    summary_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return summary_path


def write_market_quality_by_market(output_dir: Path, payload: Any) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "market_quality_by_market.json"
    data = _serialize_payload(payload)
    report_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return report_path


def write_event_lag_summary(output_dir: Path, payload: Any) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "event_lag_summary.json"
    data = _serialize_payload(payload)
    summary_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return summary_path


def write_event_rankings(output_dir: Path, payload: Any) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "event_rankings.json"
    data = _serialize_payload(payload)
    report_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return report_path
