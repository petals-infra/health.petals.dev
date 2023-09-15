from typing import Optional
from urllib.parse import urlparse

import petals
import pydantic


@pydantic.dataclasses.dataclass
class ModelInfo(petals.data_structures.ModelInfo):
    dht_prefix: Optional[str] = None
    official: bool = True
    limited: bool = False

    @property
    def name(self) -> str:
        return urlparse(self.repository).path.lstrip("/")

    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1]
