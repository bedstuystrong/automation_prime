import enum
import functools
import json
from pathlib import Path
from typing import *

import pydantic

from . import models
from .functions import inbound
from .utils import airtable

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


class Table(enum.Enum):
    INBOUND = airtable.TableSpec(
        name="inbound",
        model_cls=models.InboundModel,
        status_to_cb={None: inbound.on_new},
    )
