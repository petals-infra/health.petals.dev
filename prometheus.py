# import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from functools import partial
from typing import Counter as CounterType
from typing import List, Optional, Tuple

import numpy as np


def get_servers_payload(mrs) -> list[str]:
    servers_num_total = 0
    servers_num_relay = 0
    num_peers = 0
    pings = []
    num_ping_infs = 0
    version_counts = Counter()
    payload = ["# SERVER LEVEL METRICS"]

    for mr in mrs:
        for srv in mr["server_rows"]:
            if srv["span"].server_info is not None:
                pp = srv["span"].server_info.next_pings
                if pp is not None:
                    servers_num_total += 1
                    num_peers += len(pp)
                    pings_norm = [v for k, v in pp.items() if v != float("inf")]
                    pings.extend(pings_norm)
                    num_ping_infs += len([v for k, v in pp.items() if v == float("inf")])

                if srv["span"].server_info.using_relay:
                    servers_num_relay += 1

                ver = srv["span"].server_info.version
                if ver:
                    version_counts[ver] += 1

    if servers_num_total > 0 and pings:
        peers_per_srv = (len(pings) + num_ping_infs) / servers_num_total
        pings_inf_share = num_ping_infs / (num_ping_infs + len(pings))

        payload.extend(
            [
                f"peers_per_srv {peers_per_srv:.1f}",
                f"pings_inf_share {pings_inf_share:.3f}",
            ]
        )

    payload.append(f"servers_num_total {servers_num_total}")
    payload.append(f"servers_num_relay {servers_num_relay}")

    if pings:
        payload.append("# PINGS")
        pings = np.sort(pings).tolist()
        for pct in (25, 50, 75, 90, 95):
            payload.append(f'ping_pct{{pct="{pct}"}} {np.percentile(pings, pct):.4f}')

    payload.append("# VERSIONS")
    for version_number, version_count in version_counts.items():
        payload.append(f'server_version{{version_number="{version_number}"}} {version_count}')

    return payload


def get_models_payload(mrs) -> list[str]:
    payload = [
        "# MODEL LEVEL METRICS",
    ]

    for mr in mrs:
        model_name = mr["dht_prefix"]

        payload.append(f"# MODEL: {model_name} {'-' * 50}")

        blocks = defaultdict(lambda: np.zeros(mr["num_blocks"]))

        for srv in mr["server_rows"]:
            for block_idx in range(srv["span"].start, srv["span"].end):  # state in server.blocks:
                blocks["total"][block_idx] += 1
                blocks[srv["state"]][block_idx] += 1

                if srv["span"].server_info is not None:
                    for rps in ("network_rps", "inference_rps", "forward_rps"):
                        rps_value = getattr(srv["span"].server_info, rps, 0)
                        if rps_value is not None:
                            blocks[rps][block_idx] += rps_value

        payload.extend(
            [
                f'n_blocks{{model="{model_name}"}} {mr["num_blocks"]}',
                f'servers_num{{model="{model_name}"}} {len(mr["server_rows"])}',
                f'blocks_total{{model="{model_name}"}} {blocks["total"].sum()}',
                f'blocks_online_min{{model="{model_name}"}} {blocks["online"].min()}',
            ]
        )

        for block_state in ("online", "joining", "offline", "unreachable"):
            payload.append(f'blocks{{model="{model_name}",state="{block_state}"}} {blocks[block_state].sum():.0f}')

        for rps in ("network_rps", "inference_rps", "forward_rps"):
            rps_type = rps.split("_")[0]
            payload.append(f'rps_avg{{model="{model_name}",rps="{rps_type}"}} {blocks[rps].mean():.1f}')
            payload.append(f'rps_min{{model="{model_name}",rps="{rps_type}"}} {blocks[rps].min():.1f}')

    return payload


def get_prometheus_payload(state_dict) -> str:
    """prepares metrics in Prometeus format
    description: https://prometheus.io/docs/instrumenting/exposition_formats/
    returns multline string with single metric per line
    """

    payload = []

    # general metrics
    payload.append("# GENERAL METRICS")
    if state_dict.get("update_duration", None) is not None:
        payload.append(f"update_duration {state_dict['update_duration']:.1f}")

    # server-level metrics
    payload.extend(get_servers_payload(state_dict["model_reports"]))

    # block-level metrics
    payload.extend(get_models_payload(state_dict["model_reports"]))

    return "\n".join(payload)
    # return payload
