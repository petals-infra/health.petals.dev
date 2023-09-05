# python cli.py --model_id StableBeluga2
# Model ID: StableBeluga2, Healthy: True, Number of Blocks: 10
# TABLE WITH | Server ID | Contributor | Throughput | Served Blocks (#) |

import config
import hivemind

from utils import get_state

logger = hivemind.get_logger(__name__)

logger.info("Connecting to DHT")

dht = hivemind.DHT(initial_peers=config.INITIAL_PEERS, client_mode=False, num_workers=32, start=True)

bootstrap_peers, contrib_peers, models, reachability_issues = get_state(dht)
print(models[0])
print(models[0].keys())

print(models[0]["server_rows"][0])
print(models[0]["server_rows"][0].keys())

# Questions
# ----------------------------------------------------------------------------------
# How can I access the DHTNode object given a DHT object?
# Are model.index hard coded? `dht.get("_petals.models")`