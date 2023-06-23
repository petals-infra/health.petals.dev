from collections import defaultdict
from dataclasses import dataclass, field
from functools import partial
from typing import List, Tuple
import time

import hivemind
from flask import Flask, jsonify, render_template, request
from multiaddr import Multiaddr
from petals.data_structures import ServerState
from petals.dht_utils import get_remote_module_infos

import config
from p2p_utils import check_reachability, check_reachability_parallel


dht = hivemind.DHT(initial_peers=config.INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
app = Flask(__name__)


@dataclass
class ServerInfo:
    friendly_peer_id: str = None
    throughput: float = None
    blocks: List[Tuple[int, ServerState]] = field(default_factory=list)
    model: str = None


@app.route("/")
def main_page():
    return app.send_static_file("index.html")


@app.route("/health")
def health():
    start_time = time.time()
    bootstrap_peer_ids = []
    for addr in config.INITIAL_PEERS:
        peer_id = hivemind.PeerID.from_base58(Multiaddr(addr)["p2p"])
        if peer_id not in bootstrap_peer_ids:
            bootstrap_peer_ids.append(peer_id)

    rpc_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
    all_bootstrap_reachable = all(rpc_infos[peer_id]["ok"] for peer_id in bootstrap_peer_ids)

    block_ids = []
    for model in config.MODELS:
        block_ids += [f"{model.dht_prefix}.{i}" for i in range(model.n_blocks)]

    module_infos = get_remote_module_infos(
        dht,
        block_ids,
        float("inf"),
    )

    servers = defaultdict(ServerInfo)
    n_found_blocks = defaultdict(int)
    for info in module_infos:
        if info is None:
            continue

        dht_prefix, block_idx_str = info.uid.split('.')
        found = False
        for peer_id, server in info.servers.items():
            servers[peer_id].throughput = server.throughput
            servers[peer_id].blocks.append((int(block_idx_str), server.state))
            servers[peer_id].model = dht_prefix
            if server.state == ServerState.ONLINE:
                found = True
        n_found_blocks[dht_prefix] += found

    rpc_infos.update(dht.run_coroutine(partial(check_reachability_parallel, list(servers.keys()), fetch_info=True)))

    model_reports = []
    for model in config.MODELS:
        all_blocks_found = n_found_blocks[model.dht_prefix] == model.n_blocks
        model_state = "healthy" if all_blocks_found and all_bootstrap_reachable else "broken"

        server_rows = []
        model_servers = [(peer_id, server_info) for peer_id, server_info in servers.items() if server_info.model == model.dht_prefix]
        for peer_id, server_info in sorted(model_servers):
            block_indices = [block_idx for block_idx, state in server_info.blocks if state != ServerState.OFFLINE]
            block_indices = f"{min(block_indices)}:{max(block_indices) + 1}" if block_indices else ""

            block_map = ['<td class="block-map"> </td>' for _ in range(model.n_blocks)]
            for block_idx, state in server_info.blocks:
                state_name = state.name
                if state == ServerState.ONLINE and not rpc_infos[peer_id]["ok"]:
                    state_name = "unreachable"
                block_map[block_idx] = f'<td class="block-map">{get_state_html(state_name)}</td>'
            block_map = "".join(block_map)

            row = rpc_infos[peer_id]
            row.update(
                {
                    "short_peer_id": "..." + str(peer_id)[-12:],
                    "peer_id": peer_id,
                    "throughput": server_info.throughput,
                    "block_indices": block_indices,
                    "block_map": block_map,
                }
            )
            server_rows.append(row)

        model_reports.append({
            "repo": model.repo,
            "dht_prefix": model.dht_prefix,
            "n_blocks": model.n_blocks,
            "production": model.production,
            "state": model_state,
            "server_rows": server_rows,
        })

    bootstrap_states = "".join(
        get_state_html("online" if rpc_infos[peer_id]["ok"] else "unreachable") for peer_id in bootstrap_peer_ids
    )

    reachability_issues = [
        {"peer_id": peer_id, "err": info["error"]}
        for peer_id, info in sorted(rpc_infos.items())
        if not info["ok"]
        and (peer_id not in servers or any(state == ServerState.ONLINE for _, state in servers[peer_id].blocks))
    ]

    return render_template(
        "health.html",
        bootstrap_states=bootstrap_states,
        model_reports=model_reports,
        reachability_issues=reachability_issues,
        gen_time=(time.time() - start_time),
    )


def get_state_html(state_name: str):
    state_name = state_name.lower()
    if state_name == "offline":
        char = "_"
    elif state_name == "unreachable":
        char = "✖"
    else:
        char = "●"
    return f'<span class="{state_name}">{char}</span>'


@app.route("/api/v1/is_reachable/<peer_id>")
def api_v1_is_reachable(peer_id):
    peer_id = hivemind.PeerID.from_base58(peer_id)
    rpc_info = dht.run_coroutine(partial(check_reachability, peer_id, use_cache=False))
    return jsonify(
        success=rpc_info["ok"],
        message=rpc_info.get("error"),
        your_ip=request.remote_addr,
    )
