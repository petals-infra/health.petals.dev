import datetime
import time
import threading
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import List, Optional, Tuple

import hivemind
from multiaddr import Multiaddr
from petals.data_structures import ServerInfo, ServerState
from petals.dht_utils import get_remote_module_infos

import config
from p2p_utils import check_reachability_parallel

logger = hivemind.get_logger(__name__)


@dataclass
class MergedServerInfo:
    model: Optional[str] = None
    blocks: List[Tuple[int, ServerState]] = field(default_factory=list)
    server_info: Optional[ServerInfo] = None


class StateUpdaterThread(threading.Thread):
    def __init__(self, dht: hivemind.DHT, *, update_period: int = 60, **kwargs):
        super().__init__(**kwargs)
        self.dht = dht
        self.update_period = update_period

        self.last_state = None
        self.ready = threading.Event()

    def run(self):
        while True:
            start_time = time.perf_counter()
            try:
                self.update()
                self.ready.set()
                logger.info("Fetched new state")
            except Exception:
                logger.error("Failed to update state:", exc_info=True)

            delay = self.update_period - (time.perf_counter() - start_time)
            if delay < 0:
                logger.warning("Update took more than update_period, consider increasing it")
            time.sleep(max(delay, 0))

    def update(self) -> None:
        bootstrap_peer_ids = []
        for addr in config.INITIAL_PEERS:
            peer_id = hivemind.PeerID.from_base58(Multiaddr(addr)["p2p"])
            if peer_id not in bootstrap_peer_ids:
                bootstrap_peer_ids.append(peer_id)

        rpc_infos = self.dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
        all_bootstrap_reachable = all(rpc_infos[peer_id]["ok"] for peer_id in bootstrap_peer_ids)

        block_ids = []
        for model in config.MODELS:
            block_ids += [f"{model.dht_prefix}.{i}" for i in range(model.n_blocks)]

        module_infos = get_remote_module_infos(
            self.dht,
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
            self.dht.run_coroutine(partial(check_reachability_parallel, list(servers.keys()), fetch_info=True))
        )

        model_reports = []
        for model in config.MODELS:
            all_blocks_found = n_found_blocks[model.dht_prefix] == model.n_blocks
            model_state = "healthy" if all_blocks_found and all_bootstrap_reachable else "broken"

            server_rows = []
            model_servers = [(peer_id, server) for peer_id, server in servers.items() if server.model == model.dht_prefix]
            for peer_id, server in sorted(model_servers):
                block_indices = [block_idx for block_idx, state in server.blocks if state != ServerState.OFFLINE]
                block_indices = f"{min(block_indices)}:{max(block_indices) + 1}" if block_indices else ""

                block_map = ['<td class="block-map"> </td>' for _ in range(model.n_blocks)]
                for block_idx, state in server.blocks:
                    state_name = state.name
                    if state == ServerState.ONLINE and not rpc_infos[peer_id]["ok"]:
                        state_name = "unreachable"
                    block_map[block_idx] = f'<td class="block-map">{self._get_state_html(state_name)}</td>'
                block_map = "".join(block_map)

                row = {
                    "short_peer_id": "..." + str(peer_id)[-6:],
                    "peer_id": peer_id,
                    "block_indices": block_indices,
                    "block_map": block_map,
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
            report.update({"state": model_state, "server_rows": server_rows})
            model_reports.append(report)

        bootstrap_states = "".join(
            self._get_state_html("online" if rpc_infos[peer_id]["ok"] else "unreachable")
            for peer_id in bootstrap_peer_ids
        )

        reachability_issues = [
            {"peer_id": peer_id, "err": info["error"]}
            for peer_id, info in sorted(rpc_infos.items())
            if not info["ok"]
            and (peer_id not in servers or any(state == ServerState.ONLINE for _, state in servers[peer_id].blocks))
        ]

        self.last_state = dict(
            bootstrap_states=bootstrap_states,
            model_reports=model_reports,
            reachability_issues=reachability_issues,
            last_updated=datetime.datetime.now(datetime.timezone.utc),
            update_period=self.update_period,
        )

    @staticmethod
    def _get_state_html(state_name: str):
        state_name = state_name.lower()
        if state_name == "offline":
            char = "_"
        elif state_name == "unreachable":
            char = "✖"
        else:
            char = "●"
        return f'<span class="{state_name}">{char}</span>'
