from typing import Optional
from urllib.parse import urlparse

import petals
import pydantic


@pydantic.dataclasses.dataclass
class ModelInfo(petals.data_structures.ModelInfo):
    dht_prefix: Optional[str] = None
    official: bool = True

    @property
    def name(self) -> str:
        return urlparse(self.repository).path.lstrip("/")


INITIAL_PEERS = petals.constants.PUBLIC_INITIAL_PEERS

MODELS = [
    ModelInfo(
        dht_prefix="StableBeluga2-hf",
        repository="https://huggingface.co/petals-team/StableBeluga2",
        num_blocks=80,
    ),
    ModelInfo(
        dht_prefix="CodeLlama-34b-Instruct-hf",
        repository="https://huggingface.co/codellama/CodeLlama-34b-Instruct-hf",
        num_blocks=48,
    ),
    ModelInfo(
        dht_prefix="Llama-2-70b-chat-hf",
        repository="https://huggingface.co/meta-llama/Llama-2-70b-chat-hf",
        num_blocks=80,
    ),
    ModelInfo(
        dht_prefix="Llama-2-70b-hf",
        repository="https://huggingface.co/meta-llama/Llama-2-70b-hf",
        num_blocks=80,
    ),
    ModelInfo(
        dht_prefix="llama-65b-hf",
        repository="https://huggingface.co/huggyllama/llama-65b",
        num_blocks=80,
    ),
    ModelInfo(
        dht_prefix="bigscience/bloomz-petals",
        repository="https://huggingface.co/bigscience/bloomz",
        num_blocks=70,
    ),
    ModelInfo(
        dht_prefix="bigscience/bloom-petals",
        repository="https://huggingface.co/bigscience/bloom",
        num_blocks=70,
    ),
]
