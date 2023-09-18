import datetime
import time
from collections import Counter
from contextlib import suppress
from dataclasses import asdict
from functools import partial

import hivemind
import numpy as np
from multiaddr import Multiaddr
from petals.data_structures import UID_DELIMITER, ServerState
from petals.utils.dht import compute_spans, get_remote_module_infos

import config
from data_structures import ModelInfo
from p2p_utils import check_reachability_parallel

logger = hivemind.get_logger(__name__)


def fetch_health_state(dht: hivemind.DHT) -> dict:
    start_time = time.perf_counter()
    bootstrap_peer_ids = []
    for addr in config.INITIAL_PEERS:
        peer_id = hivemind.PeerID.from_base58(Multiaddr(addr)["p2p"])
        if peer_id not in bootstrap_peer_ids:
            bootstrap_peer_ids.append(peer_id)

    reach_infos = dht.run_coroutine(partial(check_reachability_parallel, bootstrap_peer_ids))
    bootstrap_states = ["online" if reach_infos[peer_id]["ok"] else "unreachable" for peer_id in bootstrap_peer_ids]

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

    block_uids = [f"{model.dht_prefix}{UID_DELIMITER}{i}" for model in models for i in range(model.num_blocks)]
    module_infos = get_remote_module_infos(dht, block_uids, latest=True)

    model_servers = {}
    all_servers = {}
    offset = 0
    for model in models:
        model_servers[model.dht_prefix] = compute_spans(
            module_infos[offset : offset + model.num_blocks], min_state=ServerState.OFFLINE
        )
        all_servers.update(model_servers[model.dht_prefix])
        offset += model.num_blocks

    online_servers = [peer_id for peer_id, span in all_servers.items() if span.state == ServerState.ONLINE]
    reach_infos.update(dht.run_coroutine(partial(check_reachability_parallel, online_servers, fetch_info=True)))

    top_contributors = Counter()
    model_reports = []
    for model in models:
        block_healthy = np.zeros(model.num_blocks, dtype=bool)
        server_rows = []
        for peer_id, span in sorted(model_servers[model.dht_prefix].items()):
            reachable = reach_infos[peer_id]["ok"] if peer_id in reach_infos else True
            state = span.state.name.lower() if reachable else "unreachable"
            if state == "online":
                block_healthy[span.start : span.end] = True

            show_public_name = state == "online" and span.length >= 10
            if model.official and span.server_info.public_name and show_public_name:
                top_contributors[span.server_info.public_name] += span.length

            row = {
                "short_peer_id": "..." + str(peer_id)[-6:],
                "peer_id": peer_id,
                "show_public_name": show_public_name,
                "state": state,
                "span": span,
                "adapters": [dict(name=name, short_name=name.split("/")[-1]) for name in span.server_info.adapters],
                "pings_to_me": {
                    str(origin_id): origin.server_info.next_pings[str(peer_id)]
                    for origin_id, origin in model_servers[model.dht_prefix].items()
                    if origin.server_info.next_pings is not None and str(peer_id) in origin.server_info.next_pings
                },
            }
            if span.server_info.cache_tokens_left is not None:
                # We use num_blocks * 2 to account for both keys and values
                row["cache_tokens_left_per_block"] = span.server_info.cache_tokens_left // (span.length * 2)
            server_rows.append(row)

        model_reports.append(
            dict(
                name=model.name,
                short_name=model.short_name,
                state="healthy" if block_healthy.all() else "broken",
                server_rows=server_rows,
                **asdict(model),
            )
        )

    reachability_issues = [
        dict(peer_id=peer_id, err=info["error"]) for peer_id, info in sorted(reach_infos.items()) if not info["ok"]
    ]

    return dict(
        bootstrap_states=bootstrap_states,
        top_contributors=top_contributors,
        model_reports=model_reports,
        reachability_issues=reachability_issues,
        last_updated=datetime.datetime.now(datetime.timezone.utc),
        update_period=config.UPDATE_PERIOD,
        update_duration=time.perf_counter() - start_time
    )
