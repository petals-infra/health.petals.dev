import os
from petals.constants import PUBLIC_INITIAL_PEERS

from data_structures import ModelInfo

initial_peers_str = os.getenv("INITIAL_PEERS")
initial_peers_list = initial_peers_str.split(",") if initial_peers_str else []
if len(initial_peers_list) > 0:
    INITIAL_PEERS = initial_peers_list
else:
    INITIAL_PEERS = PUBLIC_INITIAL_PEERS

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
