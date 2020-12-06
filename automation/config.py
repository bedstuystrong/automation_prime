import json
from pathlib import Path
from typing import Dict

import pydantic

CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.json"

_config = None


class AirtableConfig(pydantic.BaseModel):
    base_id: str
    api_key: str
    table_names: Dict[str, str]


class Config(pydantic.BaseModel):
    airtable: AirtableConfig

    @classmethod
    def load(cls):
        global _config

        if _config is None:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                _config = cls(**json.loads(f.read()))

        return _config
