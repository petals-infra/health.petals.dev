import asyncio
import threading
from collections import defaultdict
from functools import partial
from dataclasses import dataclass, field
from typing import List, Tuple

import hivemind
from async_timeout import timeout
from flask import Flask, jsonify, request

from petals.constants import PUBLIC_INITIAL_PEERS
from petals.data_structures import ServerState
from petals.dht_utils import get_remote_module_infos


cache_lock = threading.Lock()
reachable_cache = hivemind.TimedStorage()


async def check_for_network_errors(
    peer_id, _, node, *, connect_timeout = 5, expiration = 600, use_cache = True
):
    if use_cache and peer_id in reachable_cache:
        with cache_lock:
            return reachable_cache.get(peer_id).value

    try:
        with timeout(connect_timeout):
            await node.p2p._client.connect(peer_id, [])
            await node.p2p._client.disconnect(peer_id)

        with cache_lock:
            reachable_cache.store(peer_id, None, hivemind.get_dht_time() + expiration)
        return None
    except Exception as e:
        if isinstance(e, asyncio.TimeoutError):
            return f"Failed to connect in {connect_timeout:.0f} sec. Firewall may be blocking connections"
        message = str(e)
        message = message if message else repr(e)

        with cache_lock:
            reachable_cache.store(peer_id, message, hivemind.get_dht_time() + expiration)
        return message


async def get_network_errors(peer_ids, dht, node):
    errors = await asyncio.gather(*[check_for_network_errors(peer_id, dht, node) for peer_id in peer_ids])
    return {peer_id: err for peer_id, err in zip(peer_ids, errors) if err is not None}


dht = hivemind.DHT(initial_peers=PUBLIC_INITIAL_PEERS, client_mode=True, num_workers=32, start=True)
app = Flask(__name__)

@app.route("/")
def hello_world():
    total_blocks = 70
    module_infos = get_remote_module_infos(
        dht, [f"bigscience/bloom-petals.{i}" for i in range(total_blocks)], float("inf"),
    )
    return f"<pre>{show_module_infos(module_infos, total_blocks)}</pre>"


@app.route("/api/v1/is_reachable/<peer_id>")
def api_v1_is_reachable(peer_id):
    peer_id = hivemind.PeerID.from_base58(peer_id)
    message = dht.run_coroutine(partial(check_for_network_errors, peer_id, use_cache=False))
    return jsonify(
        success=message is None,
        message=message,
        your_ip=request.remote_addr,
    )


@dataclass
class ServerInfo:
    friendly_peer_id: str = None
    throughput: float = None
    blocks: List[Tuple[int, ServerState]] = field(default_factory=list)


def show_module_infos(module_infos, total_blocks=70):
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

    swarm_state = "healthy" if n_found_blocks == total_blocks else "broken"
    lines = [f"Swarm state: {swarm_state}\n"]

    network_errors = dht.run_coroutine(partial(get_network_errors, list(servers.keys())))

    servers = sorted(servers.items(), key=lambda item: str(item[0]))
    for peer_id, server_info in servers:
        row_name = f'{peer_id}, {server_info.throughput:.1f} RPS'
        row_name += ' ' * max(0, 63 - len(row_name))

        if peer_id in network_errors:
            state = "UNREACHABLE"

        row = [' ' for _ in range(total_blocks)]
        for block_idx, state in server_info.blocks:
            if state == ServerState.OFFLINE:
                row[block_idx] = '_'
                if peer_id in network_errors:
                    del network_errors[peer_id]
            elif peer_id in network_errors:
                row[block_idx] = '?'
            elif state == ServerState.JOINING:
                row[block_idx] = 'J'
            elif state == ServerState.ONLINE:
                row[block_idx] = '#'
        row = ''.join(row)

        lines.append(f"{row_name} |{row}|")

    lines.extend([
        "\n\nLegend:\n",
        "# - online",
        "J - joining     (loading blocks)",
        "? - unreachable (port forwarding/NAT/firewall issues, see below)",
        "_ - offline     (just disconnected)",
    ])

    if network_errors:
        lines.append("\n\nServer reachability issues:\n")
        for peer_id, err in sorted(network_errors.items(), key=lambda item: str(item[0])):
            lines.append(f'{peer_id} | {err}')
        lines.append("\nPlease ask for help in #running-a-server if you are not sure how to fix this.")

    return '\n'.join(lines)

