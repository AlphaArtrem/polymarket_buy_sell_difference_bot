from pathlib import Path

import yaml

from polymarket_arb.sources.models import SourceRegistry


def load_source_registry(path: Path) -> SourceRegistry:
    return SourceRegistry.model_validate(yaml.safe_load(path.read_text()))
