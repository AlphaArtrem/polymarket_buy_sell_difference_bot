import json
from pathlib import Path

from polymarket_arb.reporting.writers import write_structure_summary
from polymarket_arb.structure.ranking import rank_structure_relationships


def test_rank_structure_relationships_prefers_repeatable_large_gaps() -> None:
    ranked = rank_structure_relationships(
        [
            {
                "key": "steady",
                "opportunity_count": 5,
                "best_net_gap_bps": 80,
                "mean_executable_size": 10,
            },
            {
                "key": "spike",
                "opportunity_count": 1,
                "best_net_gap_bps": 150,
                "mean_executable_size": 2,
            },
        ]
    )

    assert ranked[0].key == "steady"


def test_write_structure_summary_serializes_pydantic_payload(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    path = write_structure_summary(output_dir, {"relationship_count": 2})

    assert path.name == "structure_summary.json"
    assert json.loads(path.read_text())["relationship_count"] == 2
