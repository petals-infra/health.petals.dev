from collections import Counter, defaultdict
from typing import List

import numpy as np


def get_servers_metrics(model_reports) -> List[str]:
    servers_num_total = 0
    servers_num_relay = 0
    num_peers = 0
    pings = []
    num_ping_infs = 0
    version_counts = Counter()
    result = ["# SERVER LEVEL METRICS"]

    for model_reports in model_reports:
        for server in model_reports["server_rows"]:
            if server["span"].server_info is not None:
                next_pings = server["span"].server_info.next_pings
                if next_pings is not None:
                    servers_num_total += 1
                    num_peers += len(next_pings)
                    pings_not_inf = [v for k, v in next_pings.items() if v != float("inf")]
                    pings.extend(pings_not_inf)
                    num_ping_infs += len([v for v in next_pings.values() if v == float("inf")])

                if server["span"].server_info.using_relay:
                    servers_num_relay += 1

                version = server["span"].server_info.version
                if version:
                    version_counts[version] += 1

    if servers_num_total > 0 and pings:
        peers_per_srv = (len(pings) + num_ping_infs) / servers_num_total
        pings_inf_share = num_ping_infs / (num_ping_infs + len(pings))

        result.extend(
            [
                f"peers_per_srv {peers_per_srv:.1f}",
                f"pings_inf_share {pings_inf_share:.3f}",
            ]
        )

    result.append(f"servers_num_total {servers_num_total}")
    result.append(f"servers_num_relay {servers_num_relay}")

    if pings:
        result.append("# PINGS")
        pings = np.sort(pings).tolist()
        for pct in (25, 50, 75, 90, 95):
            result.append(f'ping_pct{{pct="{pct}"}} {np.percentile(pings, pct):.4f}')

    result.append("# VERSIONS")
    for version_number, version_count in version_counts.items():
        result.append(f'server_version{{version_number="{version_number}"}} {version_count}')

    return result


def get_models_metrics(model_reports) -> List[str]:
    result = [
        "# MODEL LEVEL METRICS",
    ]

    for model_reports in model_reports:
        model_name = model_reports["dht_prefix"]

        result.append(f"# MODEL: {model_name} {'-' * 50}")

        blocks = defaultdict(lambda: np.zeros(model_reports["num_blocks"]))

        for server in model_reports["server_rows"]:
            for block_idx in range(server["span"].start, server["span"].end):
                blocks["total"][block_idx] += 1
                blocks[server["state"]][block_idx] += 1

                if server["span"].server_info is not None:
                    for rps in ("network_rps", "inference_rps", "forward_rps"):
                        rps_value = getattr(server["span"].server_info, rps, 0)
                        if rps_value is not None:
                            blocks[rps][block_idx] += rps_value

        result.extend(
            [
                f'n_blocks{{model="{model_name}"}} {model_reports["num_blocks"]}',
                f'servers_num{{model="{model_name}"}} {len(model_reports["server_rows"])}',
                f'blocks_total{{model="{model_name}"}} {blocks["total"].sum()}',
                f'blocks_online_min{{model="{model_name}"}} {blocks["online"].min()}',
            ]
        )

        for block_state in ("online", "joining", "offline", "unreachable"):
            result.append(f'blocks{{model="{model_name}",state="{block_state}"}} {blocks[block_state].sum():.0f}')

        for rps in ("network_rps", "inference_rps", "forward_rps"):
            rps_type = rps.split("_")[0]
            result.append(f'rps_avg{{model="{model_name}",rps="{rps_type}"}} {blocks[rps].mean():.1f}')
            result.append(f'rps_min{{model="{model_name}",rps="{rps_type}"}} {blocks[rps].min():.1f}')

    return result


def get_prometheus_metrics(state_dict) -> str:
    """prepares metrics in Prometeus format
    description: https://prometheus.io/docs/instrumenting/exposition_formats/
    returns multline string with single metric per line
    """
    result = []

    result.append("# GENERAL METRICS")
    result.append(f"update_duration {state_dict.get('update_duration', None):.1f}")

    result.extend(get_servers_metrics(state_dict["model_reports"]))

    result.extend(get_models_metrics(state_dict["model_reports"]))

    return "\n".join(result)
