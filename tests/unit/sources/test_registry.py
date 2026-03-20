from pathlib import Path
from textwrap import dedent

from polymarket_arb.sources.registry import load_source_registry


def test_load_source_registry_reads_market_mapping(tmp_path: Path) -> None:
    registry_path = tmp_path / "source_registry.yaml"
    registry_path.write_text(
        dedent(
            """
            sources:
              - key: sec-filing
                source_type: http_json
                url: https://example.com/api
                parser: sec_status
                market_slugs:
                  - will-example-happen
                implied_direction: yes
            """
        ).strip()
    )

    registry = load_source_registry(registry_path)

    assert registry.sources[0].key == "sec-filing"
    assert registry.sources[0].market_slugs == ["will-example-happen"]
