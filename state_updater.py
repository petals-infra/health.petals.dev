import datetime
import time
import threading
import hivemind

from flask import Flask, render_template

from petals.data_structures import ServerState

from utils import get_state

logger = hivemind.get_logger(__name__)

class StateUpdaterThread(threading.Thread):
    def __init__(self, dht: hivemind.DHT, app: Flask, update_period: int = 60, **kwargs):
        super().__init__(**kwargs)
        self.dht = dht
        self.app = app
        self.update_period = update_period

        self.last_state = None
        self.ready = threading.Event()

    def run(self):
        while True:
            start_time = time.perf_counter()
            try:
                self.update()
                self.ready.set()
                logger.info(f"Fetched new state in {time.perf_counter() - start_time:.1f} sec")
            except Exception:
                logger.error("Failed to update state:", exc_info=True)

            delay = self.update_period - (time.perf_counter() - start_time)
            if delay < 0:
                logger.warning("Update took more than update_period, consider increasing it")
            time.sleep(max(delay, 0))

    def update(self) -> None:
        bootstrap_peers, contrib_peers, models, reachability_issues = get_state(self.dht)

        for model in models:
            for server in model["server_rows"]:
                reachable = contrib_peers[server["peer_id"]]["ok"]
                block_map = ['<td class="bm"> </td>' for _ in range(model["num_blocks"])]
                for block_idx, state in server["blocks"]:
                    state_name = state.name.lower()
                    if state == ServerState.ONLINE and not reachable:
                        state_name = "unreachable"
                    block_map[block_idx] = f'<td class="bm {state_name}">{self._STATE_CHARS[state_name]}</td>'
                block_map = "".join(block_map)
                server["block_map"] = block_map
        
        bootstrap_map = "".join(
            f'<span class="{state_name}">{self._STATE_CHARS[state_name]}</span>' for state_name in bootstrap_peers
        )

        with self.app.app_context():
            self.last_state = render_template("index.html",
                bootstrap_map=bootstrap_map,
                model_reports=models,
                reachability_issues=reachability_issues,
                last_updated=datetime.datetime.now(datetime.timezone.utc),
                update_period=self.update_period,
            )

    _STATE_CHARS = {"offline": "_", "unreachable": "✖", "joining": "●", "online": "●"}
