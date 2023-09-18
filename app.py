from functools import partial

import hivemind
from flask import Flask, jsonify, request
from flask_cors import CORS

import config
from p2p_utils import check_reachability
from state_updater import StateUpdaterThread

logger = hivemind.get_logger(__name__)


logger.info("Connecting to DHT")
dht = hivemind.DHT(initial_peers=config.INITIAL_PEERS, client_mode=True, num_workers=32, start=True)

logger.info("Starting Flask app")
app = Flask(__name__)
CORS(app)

logger.info("Starting updater")
updater = StateUpdaterThread(dht, app, daemon=True)
updater.start()
updater.ready.wait()


@app.route("/")
def main_page():
    return updater.state_html


@app.route("/api/v1/state")
def api_v1_state():
    return app.response_class(response=updater.state_json, status=200, mimetype="application/json")


@app.route("/api/v1/is_reachable/<peer_id>")
def api_v1_is_reachable(peer_id):
    peer_id = hivemind.PeerID.from_base58(peer_id)
    rpc_info = dht.run_coroutine(partial(check_reachability, peer_id, use_cache=False))
    return jsonify(
        success=rpc_info["ok"],
        message=rpc_info.get("error"),
        your_ip=request.remote_addr,
    )


@app.route("/metrics")
@app.route("/api/prometheus")
def metrics():
    return app.response_class(response=updater.prometheus_metrics, status=200, mimetype="text/plain")
