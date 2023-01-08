from collections import defaultdict
from functools import partial
from dataclasses import dataclass, field
from typing import List, Tuple

import hivemind
from flask import Flask, jsonify, render_template, request
from multiaddr import Multiaddr
from petals.constants import PUBLIC_INITIAL_PEERS
from petals.data_structures import ServerState
from petals.dht_utils import get_remote_module_infos

from p2p_utils import check_reachability, check_reachability_parallel


dht = hivemind.DHT(initial_peers=PUBLIC_INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
app = Flask(__name__)


@dataclass
class ServerInfo:
    friendly_peer_id: str = None
    throughput: float = None
    blocks: List[Tuple[int, ServerState]] = field(default_factory=list)


@app.route("/")
def main_page():
    total_blocks = 70
    module_infos = get_remote_module_infos(
        dht, [f"bigscience/bloom-petals.{i}" for i in range(total_blocks)], float("inf"),
    )

    servers = defaultdict(ServerInfo)
    n_found_blocks = 0
    for block_idx, info in enumerate(module_infos):
        if info is None:
            continue

        found = False
        for peer_id, server in info.servers.items():
            servers[peer_id].throughput = server.throughput
            servers[peer_id].blocks.append((block_idx, server.state))
            if server.state == ServerState.ONLINE:
                found = True
        n_found_blocks += found
    all_blocks_found = n_found_blocks == total_blocks

    bootstrap_peer_ids = []
    for addr in PUBLIC_INITIAL_PEERS:
        peer_id = hivemind.PeerID.from_base58(Multiaddr(addr)['p2p'])
        if peer_id not in bootstrap_peer_ids:
            bootstrap_peer_ids.append(peer_id)

    network_errors = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids + list(servers.keys())))
    all_bootstrap_reachable = all(peer_id not in network_errors for peer_id in bootstrap_peer_ids)

    swarm_state = "healthy" if all_blocks_found and all_bootstrap_reachable else "broken"
    bootstrap_states = ''.join(
        get_state_html("online" if peer_id not in network_errors else "unreachable")
        for peer_id in bootstrap_peer_ids
    )

    servers = sorted(servers.items(), key=lambda item: str(item[0]))
    server_rows = []
    for peer_id, server_info in servers:
        block_indices = [block_idx for block_idx, state in server_info.blocks if state != ServerState.OFFLINE]
        block_indices = f"{min(block_indices)}:{max(block_indices) + 1}" if block_indices else ""

        block_map = [' ' for _ in range(total_blocks)]
        for block_idx, state in server_info.blocks:
            if state == ServerState.OFFLINE:
                if peer_id in network_errors:
                    del network_errors[peer_id]
            state_name = state.name if peer_id not in network_errors else "unreachable"
            block_map[block_idx] = get_state_html(state_name)
        block_map = ''.join(block_map)

        server_rows.append({
            "peer_id": peer_id,
            "throughput": server_info.throughput,
            "block_indices": block_indices,
            "block_map": block_map,
        })

    reachability_issues = [
        {"peer_id": peer_id, "err": err}
        for peer_id, err in sorted(network_errors.items(), key=lambda item: str(item[0]))
    ]

    return render_template(
        "index.html",
        swarm_state=swarm_state,
        bootstrap_states=bootstrap_states,
        server_rows=server_rows,
        reachability_issues=reachability_issues,
    )


def get_state_html(state_name: str):
    state_name = state_name.lower()
    if state_name == "offline":
        char = '_'
    elif state_name == "unreachable":
        char = '✖'
    else:
        char = '●'
    return f'<span class="{state_name}">{char}</span>'


@app.route("/api/v1/is_reachable/<peer_id>")
def api_v1_is_reachable(peer_id):
    peer_id = hivemind.PeerID.from_base58(peer_id)
    message = dht.run_coroutine(partial(check_reachability, peer_id, use_cache=False))
    return jsonify(
        success=message is None,
        message=message,
        your_ip=request.remote_addr,
    )
