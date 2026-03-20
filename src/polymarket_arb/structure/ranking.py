from pydantic import BaseModel


class RankedStructureRelationship(BaseModel):
    key: str
    opportunity_count: int
    best_net_gap_bps: float
    mean_executable_size: float
    score: float


def rank_structure_relationships(
    rows: list[dict[str, object]],
) -> list[RankedStructureRelationship]:
    ranked = [
        RankedStructureRelationship(
            key=str(row["key"]),
            opportunity_count=int(row.get("opportunity_count", 0)),
            best_net_gap_bps=float(row.get("best_net_gap_bps", 0.0)),
            mean_executable_size=float(row.get("mean_executable_size", 0.0)),
            score=(
                int(row.get("opportunity_count", 0))
                * float(row.get("best_net_gap_bps", 0.0))
                * float(row.get("mean_executable_size", 0.0))
            ),
        )
        for row in rows
    ]
    return sorted(ranked, key=lambda item: item.score, reverse=True)
