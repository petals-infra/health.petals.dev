from collections import defaultdict
from dataclasses import dataclass, field
from typing import List, Tuple

import hivemind
from flask import Flask

from petals.constants import PUBLIC_INITIAL_PEERS
from petals.data_structures import ServerState
from petals.dht_utils import get_remote_module_infos


dht = hivemind.DHT(initial_peers=PUBLIC_INITIAL_PEERS, client_mode=True, num_workers=32, start=True)

app = Flask(__name__)

@app.route("/")
def hello_world():
    total_blocks = 70
    module_infos = get_remote_module_infos(
        dht, [f"bigscience/bloom-petals.{i}" for i in range(total_blocks)], float("inf"),
    )
    return f"<pre>{show_module_infos(module_infos, total_blocks)}</pre>"


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
            servers[peer_id].friendly_peer_id = str(peer_id)
            servers[peer_id].throughput = server.throughput
            servers[peer_id].blocks.append((block_idx, server.state))
            if server.state == ServerState.ONLINE:
                found = True
        n_found_blocks += found

    swarm_state = "healthy" if n_found_blocks == total_blocks else "broken"
    lines = [f"Swarm state: {swarm_state}", ""]

    servers = sorted(servers.values(), key=lambda item: item.friendly_peer_id)
    for item in servers:
        row_name = f'{item.friendly_peer_id}, {item.throughput:.1f} RPS'
        row_name += ' ' * max(0, 21 - len(row_name))

        row = [' ' for _ in range(total_blocks)]
        for block_idx, state in item.blocks:
            if state == ServerState.ONLINE:
                row[block_idx] = '#'
            elif state == ServerState.JOINING:
                row[block_idx] = 'J'
            elif state == ServerInfo.OFFLINE:
                row[block_idx] = '_'
        row = ''.join(row)

        lines.append(f"{row_name} |{row}|")
    return '\n'.join(lines)
