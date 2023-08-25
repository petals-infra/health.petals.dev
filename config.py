from dataclasses import dataclass

from petals.constants import PUBLIC_INITIAL_PEERS


@dataclass
class ModelInfo:
    dht_prefix: str
    name: str
    href: str
    n_blocks: int
    production: bool


INITIAL_PEERS = PUBLIC_INITIAL_PEERS

MODELS = [
    ModelInfo(
        dht_prefix="StableBeluga2-hf",
        name="petals-team/StableBeluga2",
        href="https://huggingface.co/petals-team/StableBeluga2",
        n_blocks=80,
        production=True,
    ),
    ModelInfo(
        dht_prefix="CodeLlama-34b-Instruct-hf",
        name="codellama/CodeLlama-34b-Instruct-hf",
        href="https://huggingface.co/codellama/CodeLlama-34b-Instruct-hf",
        n_blocks=48,
        production=True,
    ),
    ModelInfo(
        dht_prefix="Llama-2-70b-chat-hf",
        name="meta-llama/Llama-2-70b-chat-hf",
        href="https://huggingface.co/meta-llama/Llama-2-70b-chat-hf",
        n_blocks=80,
        production=True,
    ),
    ModelInfo(
        dht_prefix="Llama-2-70b-hf",
        name="meta-llama/Llama-2-70b-hf",
        href="https://huggingface.co/meta-llama/Llama-2-70b-hf",
        n_blocks=80,
        production=True,
    ),
    ModelInfo(
        dht_prefix="llama-65b-hf",
        name="huggyllama/llama-65b",
        href="https://github.com/facebookresearch/llama/blob/main/MODEL_CARD.md",
        n_blocks=80,
        production=True,
    ),
    ModelInfo(
        dht_prefix="bigscience/bloomz-petals",
        name="bigscience/bloomz",
        href="https://huggingface.co/bigscience/bloomz",
        n_blocks=70,
        production=True,
    ),
    ModelInfo(
        dht_prefix="bigscience/bloom-petals",
        name="bigscience/bloom",
        href="https://huggingface.co/bigscience/bloom",
        n_blocks=70,
        production=True,
    ),
]
