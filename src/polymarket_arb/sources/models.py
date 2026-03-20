from pydantic import BaseModel, field_validator


class SourceDefinition(BaseModel):
    key: str
    source_type: str
    url: str
    parser: str
    market_slugs: list[str]
    implied_direction: str

    @field_validator("key", "source_type", "url", "parser", "implied_direction", mode="before")
    @classmethod
    def coerce_string_value(cls, value: object) -> str:
        if isinstance(value, bool):
            return "yes" if value else "no"
        return str(value)


class SourceRegistry(BaseModel):
    sources: list[SourceDefinition]
