from pydantic import BaseModel


class RankedEventMarket(BaseModel):
    slug: str
    accepted_signal_count: int
    median_edge_bps: float
    source_health: float
    score: float


def rank_event_markets(rows: list[dict[str, object]]) -> list[RankedEventMarket]:
    ranked = [
        RankedEventMarket(
            slug=str(row["slug"]),
            accepted_signal_count=int(row.get("accepted_signal_count", 0)),
            median_edge_bps=float(row.get("median_edge_bps", 0.0)),
            source_health=float(row.get("source_health", 0.0)),
            score=(
                int(row.get("accepted_signal_count", 0))
                * float(row.get("median_edge_bps", 0.0))
                * float(row.get("source_health", 0.0))
            ),
        )
        for row in rows
    ]
    return sorted(ranked, key=lambda item: item.score, reverse=True)
