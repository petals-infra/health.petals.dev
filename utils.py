import config
import hivemind

from petals.data_structures import ServerInfo, ServerState
from petals.utils.dht import get_remote_module_infos

from data_structures import ModelInfo
from p2p_utils import check_reachability_parallel

from collections import Counter, defaultdict
from contextlib import suppress
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import List, Optional, Tuple

from functools import partial
from multiaddr import Multiaddr

from p2p_utils import check_reachability_parallel

logger = hivemind.get_logger(__name__)

_STATE_CHARS = {"offline": "_", "unreachable": "✖", "joining": "●", "online": "●"}

@dataclass
class MergedServerInfo:
    model: Optional[str] = None
    blocks: List[Tuple[int, ServerState]] = field(default_factory=list)
    server_info: Optional[ServerInfo] = None

def get_bootstrap_peers_ids():
    bootstrap_peer_ids = []
    for addr in config.INITIAL_PEERS:
        peer_id = hivemind.PeerID.from_base58(Multiaddr(addr)["p2p"])
        if peer_id not in bootstrap_peer_ids:
            bootstrap_peer_ids.append(peer_id)
    return bootstrap_peer_ids

def get_state(dht):
    bootstrap_peer_ids = get_bootstrap_peers_ids()
    rpc_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))

    all_bootstrap_reachable = all(rpc_infos[peer_id]["ok"] for peer_id in bootstrap_peer_ids)

    bootstrap_states = ["online" if rpc_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

    reachability_issues = [
        {"peer_id": peer_id, "err": info["error"]}
        for peer_id, info in sorted(rpc_infos.items())
        if not info["ok"]
        and (peer_id not in servers or any(state == ServerState.ONLINE for _, state in servers[peer_id].blocks))
    ]
    models = config.MODELS[:]
    model_index = dht.get("_petals.models", latest=True)
    if model_index is not None and isinstance(model_index.value, dict):
        official_dht_prefixes = {model.dht_prefix for model in models}
        custom_models = []
        for dht_prefix, model in model_index.value.items():
            if dht_prefix in official_dht_prefixes:
                continue
            with suppress(TypeError, ValueError):
                model_info = ModelInfo.from_dict(model.value)
                if model_info.repository is None or not model_info.repository.startswith("https://huggingface.co/"):
                    continue
                model_info.dht_prefix = dht_prefix
                model_info.official = False
                custom_models.append(model_info)
        models.extend(sorted(custom_models, key=lambda info: (-info.num_blocks, info.dht_prefix)))
    logger.info(f"Fetching info for models {[info.name for info in models]}")

    block_ids = []
    for model in models:
        block_ids += [f"{model.dht_prefix}.{i}" for i in range(model.num_blocks)]

    module_infos = get_remote_module_infos(
        dht,
        block_ids,
        float("inf"),
    )

    servers = defaultdict(MergedServerInfo)
    n_found_blocks = defaultdict(int)
    for info in module_infos:
        if info is None:
            continue

        dht_prefix, block_idx_str = info.uid.split('.')
        found = False
        for peer_id, server_info in info.servers.items():
            servers[peer_id].model = dht_prefix
            servers[peer_id].blocks.append((int(block_idx_str), server_info.state))
            servers[peer_id].server_info = server_info
            if server_info.state == ServerState.ONLINE:
                found = True
        n_found_blocks[dht_prefix] += found
    
    rpc_infos.update(
        dht.run_coroutine(partial(check_reachability_parallel, list(servers.keys()), fetch_info=True))
    )

    contrib_peers = rpc_infos

    top_contributors = Counter()
    model_reports = []
    for model in models:
        all_blocks_found = n_found_blocks[model.dht_prefix] == model.num_blocks
        model_state = "healthy" if all_blocks_found and all_bootstrap_reachable else "broken"

        server_rows = []
        model_servers = [(peer_id, server) for peer_id, server in servers.items() if server.model == model.dht_prefix]
        for peer_id, server in sorted(model_servers):
            reachable = rpc_infos[peer_id]["ok"]
            show_public_name = (
                len(server.blocks) >= 10 and
                all(state == ServerState.ONLINE for _, state in server.blocks) and reachable
            )

            if model.official and server.server_info.public_name and show_public_name:
                top_contributors[server.server_info.public_name] += len(server.blocks)

            block_indices = [block_idx for block_idx, state in server.blocks if state != ServerState.OFFLINE]
            block_indices = f"{min(block_indices)}:{max(block_indices) + 1}" if block_indices else ""

            row = {
                "short_peer_id": "..." + str(peer_id)[-6:],
                "peer_id": peer_id,
                "show_public_name": show_public_name,
                "block_indices": block_indices,
                "blocks": server.blocks,
                "server_info": server.server_info,
                "adapters": [{"name": name, "short_name": name.split("/")[-1]} for name in server.server_info.adapters],
                "pings_to_here": [
                    {"source_id": source_id, "rtt": source.server_info.next_pings[str(peer_id)]}
                    for source_id, source in model_servers
                    if source.server_info.next_pings is not None and str(peer_id) in source.server_info.next_pings
                ],
            }
            if server.server_info.cache_tokens_left is not None:
                # We use num_blocks * 2 to account for both keys and values
                row["cache_tokens_left_per_block"] = server.server_info.cache_tokens_left // (len(server.blocks) * 2)
            server_rows.append(row)

        report = asdict(model)
        report.update(name=model.name, short_name=model.short_name, state=model_state, server_rows=server_rows)
        model_reports.append(report)

    return bootstrap_states, contrib_peers, top_contributors, model_reports, reachability_issues