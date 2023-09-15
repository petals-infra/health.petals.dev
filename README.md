# Petals Health Monitor

Source code for the Petals health monitor: https://health.petals.dev

```
Swarm state: healthy

...2vYiga, 256.0 RPS  |                                 ########                             |
...vMfXzi, 3688.5 RPS |#########################                                             |
...i9CA9T, 2776.2 RPS |                              ###############                         |
...33Pgb9, 2108.6 RPS |###############                                                       |
...Ap3RUq, 256.0 RPS  |                                     ########                         |
...7mhsNH, 256.0 RPS  |                         ########                                     |
...iRUz6M, 2767.3 RPS |               ###############                                        |
...zbDrjo, 3500.3 RPS |                                             #########################|


Legend:

# - online
J - joining     (loading blocks)
? - unreachable (port forwarding/NAT/firewall issues, see below)
_ - offline     (just disconnected)
```

See more info about Petals in its [main GitHub repo](https://github.com/bigscience-workshop/petals).

## Installation

You can run this app on your server using these commands:

```bash
git clone https://github.com/petals-infra/health.petals.dev
cd health.petals.dev
pip install -r requirements.txt
flask run --host=0.0.0.0 --port=5000
```

In production, we recommend using gunicorn instead of the Flask dev server:

```bash
gunicorn app:app --bind 0.0.0.0:5000 --workers 4 --threads 10
```

<details>
<summary><b>Running with Docker</b></summary>

```bash
git clone https://github.com/petals-infra/health.petals.dev
cd health.petals.dev
docker-compose up --build -d
```
</details>

### Monitoring private swarm

To monitor your private swarm instead of the public one, please replace `PUBLIC_INITIAL_PEERS` with a list of multiaddresses of your swarm's **initial peers** in [config.py](config.py). Example:

```python
INITIAL_PEERS = ['/ip4/10.1.2.3/tcp/31234/p2p/QmcXhze98AcgGQDDYna23s4Jho96n8wkwLJv78vxtFNq44']
```

## HTTP API

- **GET /api/v1/state** ([example](https://health.petals.dev/api/v1/state))

    This call returns a large JSON that contains all data used for rendering the [health monitor page](https://health.petals.dev/).

    Note that we regularly update the info shown there, so the response format may change at any time. We expect most changes to be minor.
    If this is still an issue for you, you can clone this repository and launch your own API endpoint with a fixed version of the code.
    Alternatively, you can use Python API directly from your script (see below).

- **GET /api/v1/is_reachable/`<peer_id>`**

    Check if the health monitor can reach a libp2p node with given `peer_id`.
    Petals servers use this call to ping themselves and ensure that they are reachable before announcing their ONLINE status to the swarm.
    For example, if the server is located behind NAT without ports forwarded,
    this ensures that libp2p has successfully found a relay needed for NAT traversal.

    Returns (JSON):

    - **ok** (bool) - whether the node is reachable
    - **message** (str) - an error message if `ok == False`
    - **your_ip** (str) - the IP address of the caller

## Python API

You can clone this repository and access the health monitor state directly from Python by running a `hivemind.DHT` client:

```python
# git clone https://github.com/petals-infra/health.petals.dev
# cd health.petals.dev

from pprint import pprint
import hivemind
from petals.constants import PUBLIC_INITIAL_PEERS
from health import fetch_health_state

dht = hivemind.DHT(initial_peers=PUBLIC_INITIAL_PEERS, client_mode=True, start=True)
pprint(fetch_health_state(dht))
```
