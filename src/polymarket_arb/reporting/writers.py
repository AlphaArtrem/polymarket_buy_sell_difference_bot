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
