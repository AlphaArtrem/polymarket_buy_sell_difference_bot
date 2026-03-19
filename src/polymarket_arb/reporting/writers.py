import json
from pathlib import Path
from typing import Any, Dict

from polymarket_arb.domain.models import MarketCatalogEntry


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
    if hasattr(payload, "model_dump"):
        data = payload.model_dump()
    else:
        data = payload
    summary_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return summary_path
