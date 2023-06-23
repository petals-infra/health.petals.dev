from dataclasses import dataclass

from petals.constants import PUBLIC_INITIAL_PEERS


@dataclass
class ModelInfo:
    dht_prefix: str
    repo: str
    n_blocks: int
    production: bool


INITIAL_PEERS = PUBLIC_INITIAL_PEERS

MODELS = [
    ModelInfo(dht_prefix="llama-65b-hf", repo="enoch/llama-65b-hf", n_blocks=80, production=True),
    ModelInfo(dht_prefix="bigscience/bloom-petals", repo="bigscience/bloom", n_blocks=70, production=True),
    ModelInfo(dht_prefix="bigscience/bloomz-petals", repo="bigscience/bloomz", n_blocks=70, production=True),
]
