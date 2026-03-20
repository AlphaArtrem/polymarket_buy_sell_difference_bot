from pydantic import BaseModel


class StructureDefinition(BaseModel):
    key: str
    relationship_type: str
    market_slugs: list[str]


class StructureOpportunity(BaseModel):
    key: str
    relationship_type: str
    raw_gap_bps: float
    net_gap_bps: float
    executable_size: float
